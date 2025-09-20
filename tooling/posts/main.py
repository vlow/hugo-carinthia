#!/usr/bin/env python3
"""
Post Processing Tool

A tool to process and edit Hugo posts, projects, blips, and library posts with AI assistance.
Provides formatting, proofreading, and copyediting capabilities with undo/redo functionality.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re
import shutil
import unicodedata

# Add parent directory to path to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.config import config_manager

# Try to import OpenAI - it's optional
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    openai = None

# Import formatting utility
from format_content import format_content, parse_hugo_content


class VersionStack:
    """Manages undo/redo stack for content versions."""

    def __init__(self):
        self.versions: List[str] = []
        self.current_index: int = -1

    def push(self, content: str) -> None:
        """Add new version and clear any redo history."""
        # Remove any versions after current index (redo history)
        self.versions = self.versions[:self.current_index + 1]
        self.versions.append(content)
        self.current_index = len(self.versions) - 1

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.current_index > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.current_index < len(self.versions) - 1

    def undo(self) -> Optional[str]:
        """Move back one version."""
        if self.can_undo():
            self.current_index -= 1
            return self.versions[self.current_index]
        return None

    def redo(self) -> Optional[str]:
        """Move forward one version."""
        if self.can_redo():
            self.current_index += 1
            return self.versions[self.current_index]
        return None

    def current(self) -> Optional[str]:
        """Get current version."""
        if 0 <= self.current_index < len(self.versions):
            return self.versions[self.current_index]
        return None


class PostInfo:
    """Information about a post file."""

    def __init__(self, path: Path, post_type: str, title: str = "", date: datetime = None):
        self.path = path
        self.post_type = post_type  # 'post', 'project', 'blip', 'library'
        self.title = title
        self.date = date or datetime.fromtimestamp(path.stat().st_mtime)

    def __str__(self) -> str:
        date_str = self.date.strftime("%Y-%m-%d")
        return f"[{self.post_type.upper()}] {date_str} - {self.title or self.path.stem}"


class PostProcessor:
    """Main post processing tool."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tooling_root = project_root / "tooling" / "posts"
        self.prompts_dir = self.tooling_root / "prompts"
        self.version_stack = VersionStack()

        # Check if OpenAI is available and API key exists
        self.has_openai_key = HAS_OPENAI and config_manager.has_api_key('OPENAI_API_KEY')

        # Initialize OpenAI client if available and key exists
        if self.has_openai_key:
            api_key = config_manager.get_api_key('OPENAI_API_KEY')
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            self.openai_client = None

    def slugify(self, text: str, max_length: int = 50) -> str:
        """
        Convert text to a filesystem-safe slug.

        Args:
            text: Text to slugify
            max_length: Maximum length of the slug

        Returns:
            Slugified text
        """
        if not text:
            return ""

        # Normalize unicode characters
        text = unicodedata.normalize('NFD', text)

        # Convert to lowercase and handle common accented characters
        text = text.lower()

        # Replace accented characters with base characters
        replacements = {
            'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
            'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
            'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
            'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
            'ñ': 'n', 'ç': 'c'
        }

        for accented, base in replacements.items():
            text = text.replace(accented, base)

        # Remove non-alphanumeric characters except spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)

        # Replace multiple spaces/whitespace with single hyphens
        text = re.sub(r'\s+', '-', text)

        # Remove leading/trailing hyphens
        text = text.strip('-')

        # Limit length and ensure we don't cut off in the middle of a word
        if len(text) > max_length:
            text = text[:max_length].rstrip('-')
            # Find last hyphen to avoid cutting words
            last_hyphen = text.rfind('-')
            if last_hyphen > max_length * 0.7:  # If hyphen is reasonably close to end
                text = text[:last_hyphen]

        return text or "untitled"

    def re_slug_post(self, post_info: PostInfo) -> Optional[PostInfo]:
        """
        Re-slug a post based on its current title.

        Args:
            post_info: Current post information

        Returns:
            Updated PostInfo if successful, None if failed
        """
        try:
            # Read current content to extract title
            content = post_info.path.read_text(encoding='utf-8')
            frontmatter, body = parse_hugo_content(content)

            if not frontmatter:
                print("Error: No frontmatter found in post.")
                return None

            # Extract current title from frontmatter
            current_title = ""
            for line in frontmatter.split('\n'):
                line = line.strip()
                if line.startswith('title = '):
                    current_title = line.split('=', 1)[1].strip().strip("'\"")
                    break

            if not current_title:
                print("Error: No title found in frontmatter.")
                return None

            # Generate new slug from current title
            new_slug = self.slugify(current_title)

            # Determine post type and handle accordingly
            if post_info.post_type == 'post':
                return self._re_slug_post_bundle(post_info, new_slug)
            elif post_info.post_type == 'project':
                return self._re_slug_project_file(post_info, new_slug)
            else:
                print(f"Re-slugging not supported for post type: {post_info.post_type}")
                return None

        except Exception as e:
            print(f"Error re-slugging post: {e}")
            return None

    def _re_slug_post_bundle(self, post_info: PostInfo, new_slug: str) -> Optional[PostInfo]:
        """Re-slug a post bundle (directory with index.md)."""
        old_path = post_info.path
        old_dir = old_path.parent

        # Check if this is actually a bundle
        if old_path.name != 'index.md':
            print("Error: Expected bundle structure with index.md")
            return None

        # Generate new directory path
        posts_dir = old_dir.parent
        new_dir = posts_dir / new_slug

        # Check if target already exists
        if new_dir.exists() and new_dir != old_dir:
            counter = 1
            while True:
                new_dir = posts_dir / f"{new_slug}-{counter}"
                if not new_dir.exists():
                    break
                counter += 1
            new_slug = f"{new_slug}-{counter}"

        if new_dir == old_dir:
            print("Slug is already current.")
            return post_info

        # Move the directory
        print(f"Renaming directory: {old_dir.name} → {new_dir.name}")
        old_dir.rename(new_dir)

        # Update post info
        new_post_info = PostInfo(
            new_dir / 'index.md',
            post_info.post_type,
            post_info.title,
            post_info.date
        )

        return new_post_info

    def _re_slug_project_file(self, post_info: PostInfo, new_slug: str) -> Optional[PostInfo]:
        """Re-slug a project file."""
        old_path = post_info.path
        projects_dir = old_path.parent
        new_path = projects_dir / f"{new_slug}.md"

        # Check if target already exists
        if new_path.exists() and new_path != old_path:
            counter = 1
            while True:
                new_path = projects_dir / f"{new_slug}-{counter}.md"
                if not new_path.exists():
                    break
                counter += 1
            new_slug = f"{new_slug}-{counter}"

        if new_path == old_path:
            print("Slug is already current.")
            return post_info

        # Move the file
        print(f"Renaming file: {old_path.name} → {new_path.name}")
        old_path.rename(new_path)

        # Update post info
        new_post_info = PostInfo(
            new_path,
            post_info.post_type,
            post_info.title,
            post_info.date
        )

        return new_post_info

    def find_all_posts(self) -> List[PostInfo]:
        """Find all posts across different content types."""
        posts = []

        # Find blog posts
        posts_dir = self.project_root / "content" / "posts"
        if posts_dir.exists():
            for item in posts_dir.iterdir():
                if item.is_file() and item.suffix == '.md' and item.name != '_index.md':
                    post_info = self._extract_post_info(item, 'post')
                    posts.append(post_info)
                elif item.is_dir():
                    index_file = item / 'index.md'
                    if index_file.exists():
                        post_info = self._extract_post_info(index_file, 'post')
                        posts.append(post_info)

        # Find projects
        projects_dir = self.project_root / "content" / "projects"
        if projects_dir.exists():
            for item in projects_dir.iterdir():
                if item.is_file() and item.suffix == '.md' and item.name != '_index.md':
                    post_info = self._extract_post_info(item, 'project')
                    posts.append(post_info)

        # Find blips
        blips_dir = self.project_root / "content" / "blips"
        if blips_dir.exists():
            for item in blips_dir.iterdir():
                if item.is_file() and item.suffix == '.md' and item.name != '_index.md':
                    post_info = self._extract_post_info(item, 'blip')
                    posts.append(post_info)

        # Find library posts
        library_dir = self.project_root / "content" / "library"
        if library_dir.exists():
            for item in library_dir.iterdir():
                if item.is_dir():
                    index_file = item / 'index.md'
                    if index_file.exists():
                        post_info = self._extract_post_info(index_file, 'library')
                        posts.append(post_info)

        # Sort by date (newest first)
        posts.sort(key=lambda x: x.date, reverse=True)

        return posts

    def _extract_post_info(self, file_path: Path, post_type: str) -> PostInfo:
        """Extract title and date from a post file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            frontmatter, _ = parse_hugo_content(content)

            # Extract title and date from frontmatter
            title = ""
            date = None

            if frontmatter:
                # Simple TOML parsing for title and date
                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if line.startswith('title = '):
                        title = line.split('=', 1)[1].strip().strip("'\"")
                    elif line.startswith('date = '):
                        date_str = line.split('=', 1)[1].strip().strip("'\"")
                        try:
                            # Try to parse ISO format date
                            if 'T' in date_str:
                                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            else:
                                date = datetime.fromisoformat(date_str)
                        except:
                            pass

            if not date:
                date = datetime.fromtimestamp(file_path.stat().st_mtime)

            return PostInfo(file_path, post_type, title, date)

        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return PostInfo(file_path, post_type, file_path.stem,
                          datetime.fromtimestamp(file_path.stat().st_mtime))

    def show_post_selection(self, posts: List[PostInfo], page: int = 0, page_size: int = 10) -> Optional[PostInfo]:
        """Show paginated post selection menu."""
        if not posts:
            print("No posts found.")
            return None

        total_pages = (len(posts) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(posts))
        current_posts = posts[start_idx:end_idx]

        print(f"\nFound {len(posts)} posts (Page {page + 1}/{total_pages}):")
        print()

        for i, post in enumerate(current_posts, 1):
            print(f"{i}. {post}")

        print()
        options = []
        if page > 0:
            options.append("p. Previous page")
        if page < total_pages - 1:
            options.append("n. Next page")
        options.append("q. Quit")

        for option in options:
            print(option)

        while True:
            try:
                choice = input(f"\nSelect post (1-{len(current_posts)}) or option: ").strip().lower()

                if choice == 'q':
                    return None
                elif choice == 'p' and page > 0:
                    return self.show_post_selection(posts, page - 1, page_size)
                elif choice == 'n' and page < total_pages - 1:
                    return self.show_post_selection(posts, page + 1, page_size)
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(current_posts):
                            return current_posts[idx]
                        print("Invalid selection.")
                    except ValueError:
                        print("Invalid input.")
            except (KeyboardInterrupt, EOFError):
                return None

    def get_prompts(self) -> List[Path]:
        """Get list of available prompt files."""
        if not self.prompts_dir.exists():
            return []

        return sorted(self.prompts_dir.glob("*.txt"))

    def select_prompt(self) -> Optional[Path]:
        """Let user select a prompt file."""
        prompts = self.get_prompts()

        if not prompts:
            print("No prompt files found in prompts directory.")
            print(f"Create prompt files in: {self.prompts_dir}")
            return None

        if len(prompts) == 1:
            print(f"Using prompt: {prompts[0].stem}")
            return prompts[0]

        print("\nAvailable prompts:")
        for i, prompt_file in enumerate(prompts, 1):
            print(f"{i}. {prompt_file.stem}")

        while True:
            try:
                choice = int(input("\nSelect prompt (number): ")) - 1
                if 0 <= choice < len(prompts):
                    return prompts[choice]
                print("Invalid selection.")
            except (ValueError, KeyboardInterrupt):
                return None

    def format_post(self, post_path: Path) -> bool:
        """Format post content to have one sentence per line."""
        try:
            original_content = post_path.read_text(encoding='utf-8')
            formatted_content = format_content(original_content)

            if original_content != formatted_content:
                # Add to version stack before making changes
                self.version_stack.push(original_content)
                post_path.write_text(formatted_content, encoding='utf-8')
                print("Content formatted (one sentence per line).")
                return True
            else:
                print("Content already properly formatted.")
                return False

        except Exception as e:
            print(f"Error formatting content: {e}")
            return False

    def process_with_ai(self, post_path: Path, prompt_path: Path) -> bool:
        """Process post content using AI with the selected prompt."""
        if not self.has_openai_key:
            print("Error: No OpenAI API key available.")
            return False

        try:
            # Read post content
            post_content = post_path.read_text(encoding='utf-8')
            frontmatter, body = parse_hugo_content(post_content)

            if not body.strip():
                print("No content to process.")
                return False

            # Read prompt
            prompt_content = prompt_path.read_text(encoding='utf-8')

            print(f"Processing with prompt: {prompt_path.stem}")
            print("Calling OpenAI API...")

            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompt_content},
                    {"role": "user", "content": body}
                ],
                temperature=0.3
            )

            ai_result = response.choices[0].message.content

            # Format the AI result to maintain consistency
            formatted_result = format_content(ai_result)

            # Reconstruct full content
            if frontmatter:
                full_result = f"{frontmatter}\n\n{formatted_result}"
            else:
                full_result = formatted_result

            # Present options to user
            return self._handle_ai_result(post_path, full_result)

        except Exception as e:
            print(f"Error processing with AI: {e}")
            return False

    def _handle_ai_result(self, post_path: Path, ai_result: str) -> bool:
        """Handle AI processing result - let user choose direct edit or vimdiff."""
        print("\nAI processing complete. How would you like to handle the result?")
        print("1. Replace content directly and open in editor")
        print("2. Review changes with vimdiff")
        print("3. Cancel")

        while True:
            try:
                choice = input("\nSelect option (1-3): ").strip()

                if choice == '1':
                    return self._direct_edit(post_path, ai_result)
                elif choice == '2':
                    return self._vimdiff_review(post_path, ai_result)
                elif choice == '3':
                    print("AI result cancelled.")
                    return False
                else:
                    print("Invalid choice.")
            except (KeyboardInterrupt, EOFError):
                return False

    def _direct_edit(self, post_path: Path, new_content: str) -> bool:
        """Replace content directly and open in editor."""
        try:
            # Save current content to version stack
            original_content = post_path.read_text(encoding='utf-8')
            self.version_stack.push(original_content)

            # Write new content
            post_path.write_text(new_content, encoding='utf-8')
            print("Content updated.")

            # Open in editor
            editor = config_manager.get_editor()
            if editor:
                print(f"Opening in editor: {editor}")
                subprocess.run([editor, str(post_path)])

            return True

        except Exception as e:
            print(f"Error in direct edit: {e}")
            return False

    def _vimdiff_review(self, post_path: Path, ai_result: str) -> bool:
        """Review changes using vimdiff."""
        try:
            # Save current content to version stack
            original_content = post_path.read_text(encoding='utf-8')
            self.version_stack.push(original_content)

            # Create temporary file for AI result
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                tmp_file.write(ai_result)
                tmp_path = tmp_file.name

            try:
                print("Opening vimdiff for change review...")
                print("Save and exit to accept changes, or exit without saving to reject.")

                # Run vimdiff
                result = subprocess.run(['vimdiff', str(post_path), tmp_path])

                if result.returncode == 0:
                    print("Changes reviewed.")
                else:
                    print("vimdiff exited with error.")

                return True

            finally:
                # Clean up temporary file
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            print(f"Error in vimdiff review: {e}")
            return False

    def undo_changes(self, post_path: Path) -> bool:
        """Undo last change."""
        content = self.version_stack.undo()
        if content:
            post_path.write_text(content, encoding='utf-8')
            print("Undid last change.")
            return True
        else:
            print("Nothing to undo.")
            return False

    def redo_changes(self, post_path: Path) -> bool:
        """Redo last undone change."""
        content = self.version_stack.redo()
        if content:
            post_path.write_text(content, encoding='utf-8')
            print("Redid last change.")
            return True
        else:
            print("Nothing to redo.")
            return False

    def show_main_menu(self, post_info: PostInfo) -> str:
        """Show main menu and get user choice."""
        print(f"\nProcessing: {post_info}")
        print(f"File: {post_info.path}")
        print("\nOptions:")

        options = []
        option_map = {}
        current_option = 1

        if self.has_openai_key and self.get_prompts():
            print(f"{current_option}. Process with AI prompt")
            option_map[str(current_option)] = 'ai_prompt'
            current_option += 1

        print(f"{current_option}. Edit manually")
        option_map[str(current_option)] = 'edit'
        current_option += 1

        print(f"{current_option}. Format content (sentence per line)")
        option_map[str(current_option)] = 'format'
        current_option += 1

        # Add re-slug option for posts and projects
        if post_info.post_type in ['post', 'project']:
            print(f"{current_option}. Re-slug from current title")
            option_map[str(current_option)] = 're_slug'
            current_option += 1

        print(f"{current_option}. Select different post")
        option_map[str(current_option)] = 'select'
        current_option += 1

        print(f"{current_option}. Exit")
        option_map[str(current_option)] = 'exit'

        # Add undo/redo options
        if self.version_stack.can_undo() or self.version_stack.can_redo():
            print()

        if self.version_stack.can_undo():
            print("u. Undo")

        if self.version_stack.can_redo():
            print("r. Redo")

        while True:
            try:
                choice = input("\nSelect option: ").strip().lower()
                valid_choices = list(option_map.keys())

                if self.version_stack.can_undo():
                    valid_choices.append('u')
                if self.version_stack.can_redo():
                    valid_choices.append('r')

                if choice in valid_choices:
                    return option_map.get(choice, choice)
                print("Invalid choice.")
            except (KeyboardInterrupt, EOFError):
                return 'exit'

    def run_interactive(self, initial_post_path: Optional[Path] = None):
        """Run the interactive post processing interface."""
        posts = self.find_all_posts()

        if not posts:
            print("No posts found in the project.")
            return

        # Select initial post
        if initial_post_path:
            # Find the post info for the given path
            selected_post = None
            for post in posts:
                if post.path == initial_post_path:
                    selected_post = post
                    break

            if not selected_post:
                print(f"Error: Post not found: {initial_post_path}")
                return
        else:
            selected_post = self.show_post_selection(posts)
            if not selected_post:
                return

        # Initialize version stack with current content
        current_content = selected_post.path.read_text(encoding='utf-8')
        self.version_stack.push(current_content)

        # Auto-format the post on selection
        print(f"Auto-formatting post: {selected_post.title or selected_post.path.stem}")
        self.format_post(selected_post.path)

        # Main processing loop
        while True:
            choice = self.show_main_menu(selected_post)

            if choice == 'exit':
                break
            elif choice == 'select':
                new_post = self.show_post_selection(posts)
                if new_post:
                    selected_post = new_post
                    # Reset version stack for new post
                    self.version_stack = VersionStack()
                    current_content = selected_post.path.read_text(encoding='utf-8')
                    self.version_stack.push(current_content)
                    # Auto-format the newly selected post
                    print(f"Auto-formatting post: {selected_post.title or selected_post.path.stem}")
                    self.format_post(selected_post.path)
            elif choice == 'format':
                self.format_post(selected_post.path)
            elif choice == 're_slug':
                new_post_info = self.re_slug_post(selected_post)
                if new_post_info:
                    selected_post = new_post_info
                    # Reset version stack for re-slugged post
                    self.version_stack = VersionStack()
                    current_content = selected_post.path.read_text(encoding='utf-8')
                    self.version_stack.push(current_content)
            elif choice == 'ai_prompt':
                prompt = self.select_prompt()
                if prompt:
                    self.process_with_ai(selected_post.path, prompt)
            elif choice == 'edit':
                editor = config_manager.get_editor()
                if editor:
                    print(f"Opening in editor: {editor}")
                    subprocess.run([editor, str(selected_post.path)])
                else:
                    print("No editor configured.")
            elif choice == 'u':
                self.undo_changes(selected_post.path)
            elif choice == 'r':
                self.redo_changes(selected_post.path)

        print("Goodbye!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Process Hugo posts with AI assistance')
    parser.add_argument('post_path', nargs='?', help='Path to specific post file to process')

    args = parser.parse_args()

    # Find project root
    current_dir = Path.cwd()
    project_root = None

    # Look for content directory or other Hugo indicators
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / 'content').exists() and (parent / 'content').is_dir():
            project_root = parent
            break

    if not project_root:
        print("Error: Could not find Hugo project root.")
        print("Please run this script from within a Hugo project directory.")
        sys.exit(1)

    # Initialize processor
    processor = PostProcessor(project_root)

    # Handle specific post path if provided
    initial_post_path = None
    if args.post_path:
        initial_post_path = Path(args.post_path).resolve()
        if not initial_post_path.exists():
            print(f"Error: File not found: {args.post_path}")
            sys.exit(1)

    # Run interactive interface
    processor.run_interactive(initial_post_path)


if __name__ == "__main__":
    main()
