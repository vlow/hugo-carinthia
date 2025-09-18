#!/usr/bin/env python3
"""
Blip Creation Tool

A tool to create and edit Hugo blip posts with AI-powered editing capabilities.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

import openai


class VersionStack:
    """Manages undo/redo stack for blip content versions."""

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


class BlipTool:
    """Main blip creation and editing tool."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tooling_root = project_root / "tooling" / "blips"
        self.prompts_dir = self.tooling_root / "prompts"
        self.config_file = self.tooling_root / "config.json"
        self.version_stack = VersionStack()

        # Load configuration
        self.config = self.load_config()

        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        default_config = {
            "deploy_target": "ssh://tc3.eu/var/www/"
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except (json.JSONDecodeError, IOError):
                pass

        return default_config

    def save_config(self):
        """Save configuration to JSON file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def find_editor(self) -> str:
        """Find available text editor."""
        # Check EDITOR environment variable first
        editor = os.getenv('EDITOR')
        if editor:
            return editor

        # Try common editors
        for editor in ['vim', 'nano']:
            if subprocess.run(['which', editor], capture_output=True).returncode == 0:
                return editor

        print("Error: No text editor found. Please set EDITOR environment variable or install vim/nano.")
        sys.exit(1)

    def create_blip_file(self) -> Path:
        """Create a new blip file with archetype template."""
        # Generate timestamp and filename
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        filename = f"blip-{now.strftime('%Y%m%d-%H%M%S')}.md"

        # Create blip content from archetype
        content = f"""+++
title = 'New Blip'
date = {now.isoformat()}
draft = false
tags = []
+++

"""

        blip_path = self.project_root / "content" / "blips" / filename
        blip_path.write_text(content)

        return blip_path

    def edit_file(self, file_path: Path) -> bool:
        """Open file in editor and return True if saved."""
        editor = self.find_editor()

        # Get original modification time
        orig_mtime = file_path.stat().st_mtime if file_path.exists() else 0

        # Build editor command with vim-specific options
        if 'vim' in editor.lower():
            # Start vim with cursor at first content line after frontmatter
            # For our blip template, content starts at line 8 (after frontmatter + blank line)
            cmd = [editor, '+8', str(file_path)]
        else:
            cmd = [editor, str(file_path)]

        # Open editor
        result = subprocess.run(cmd)

        if result.returncode != 0:
            return False

        # Check if file was modified
        if not file_path.exists():
            return False

        new_mtime = file_path.stat().st_mtime
        return new_mtime > orig_mtime

    def get_prompts(self) -> List[Path]:
        """Get list of available prompt files."""
        if not self.prompts_dir.exists():
            return []

        return list(self.prompts_dir.glob("*.txt"))

    def select_prompt(self) -> Optional[Path]:
        """Let user select a prompt file."""
        prompts = self.get_prompts()

        if not prompts:
            print("No prompt files found in prompts directory.")
            return None

        if len(prompts) == 1:
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

    def parse_hugo_content(self, full_content: str) -> tuple[str, str]:
        """Parse Hugo content into frontmatter and body content."""
        lines = full_content.split('\n')

        if not lines or not lines[0].strip() == '+++':
            # No frontmatter found
            return '', full_content

        # Find end of frontmatter
        frontmatter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '+++':
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            # No closing +++, treat as no frontmatter
            return '', full_content

        frontmatter = '\n'.join(lines[:frontmatter_end + 1])
        content = '\n'.join(lines[frontmatter_end + 1:]).lstrip('\n')

        return frontmatter, content

    def reconstruct_hugo_content(self, frontmatter: str, content: str) -> str:
        """Reconstruct full Hugo content from frontmatter and body."""
        if not frontmatter:
            return content

        return frontmatter + '\n\n' + content

    def call_openai(self, content: str, prompt: str) -> str:
        """Call OpenAI API with content and prompt."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o as gpt-5 isn't available yet
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return content

    def copyread_blip(self, blip_path: Path) -> bool:
        """Run copyread process on blip."""
        prompt_file = self.select_prompt()
        if not prompt_file:
            return False

        # Read prompt and current content
        prompt = prompt_file.read_text().strip()
        full_content = blip_path.read_text()

        # Parse frontmatter and content
        frontmatter, content = self.parse_hugo_content(full_content)

        print(f"\nProcessing with prompt: {prompt_file.stem}")
        processed_content = self.call_openai(content, prompt)

        # Reconstruct full content with original frontmatter
        full_processed_content = self.reconstruct_hugo_content(frontmatter, processed_content)

        # Save to version stack and update file
        self.version_stack.push(full_processed_content)
        blip_path.write_text(full_processed_content)

        # Open in editor
        return self.edit_file(blip_path)

    def custom_ai_processing(self, blip_path: Path) -> bool:
        """Run custom AI processing on blip."""
        user_prompt = input("\nEnter your custom prompt: ").strip()
        if not user_prompt:
            return False

        # Enhance prompt to return only processed content
        enhanced_prompt = f"""Process the following text according to this instruction: {user_prompt}

Return ONLY the processed text content, without any additional commentary, explanations, or meta-text like "Here is your edited version:" or similar. Just return the direct result."""

        # Process content
        full_content = blip_path.read_text()

        # Parse frontmatter and content
        frontmatter, content = self.parse_hugo_content(full_content)

        processed_content = self.call_openai(content, enhanced_prompt)

        # Reconstruct full content with original frontmatter
        full_processed_content = self.reconstruct_hugo_content(frontmatter, processed_content)

        # Save to version stack and update file
        self.version_stack.push(full_processed_content)
        blip_path.write_text(full_processed_content)

        # Open in editor
        return self.edit_file(blip_path)

    def undo_changes(self, blip_path: Path) -> bool:
        """Undo last change."""
        content = self.version_stack.undo()
        if content:
            blip_path.write_text(content)
            print("Undid last change.")
            return True
        else:
            print("Nothing to undo.")
            return False

    def redo_changes(self, blip_path: Path) -> bool:
        """Redo last undone change."""
        content = self.version_stack.redo()
        if content:
            blip_path.write_text(content)
            print("Redid last change.")
            return True
        else:
            print("Nothing to redo.")
            return False

    def deploy_blip(self) -> bool:
        """Deploy the blog."""
        deploy_script = self.project_root / "deploy.sh"

        if not deploy_script.exists():
            print(f"Error: deploy.sh not found at {deploy_script}")
            return False

        print("Deploying blog...")
        result = subprocess.run([str(deploy_script)], cwd=self.project_root)
        return result.returncode == 0

    def show_menu(self, blip_path: Path) -> str:
        """Show main menu and get user choice."""
        print(f"\nBlip file: {blip_path.name}")
        print("\nOptions:")
        print("1. Copyread (Predefined Prompts)")
        print("2. Prompt Changes (GPT)")
        print("3. Edit manually")
        print("4. Publish")
        print("5. Exit")

        # Add undo/redo options with separator
        if self.version_stack.can_undo() or self.version_stack.can_redo():
            print()  # Empty line separator

        if self.version_stack.can_undo():
            print("u. Undo")

        if self.version_stack.can_redo():
            print("r. Redo")

        while True:
            try:
                choice = input("\nSelect option: ").strip().lower()
                valid_choices = ['1', '2', '3', '4', '5']

                if self.version_stack.can_undo():
                    valid_choices.append('u')
                if self.version_stack.can_redo():
                    valid_choices.append('r')

                if choice in valid_choices:
                    return choice
                print("Invalid choice.")
            except (KeyboardInterrupt, EOFError):
                return '5'

    def run(self):
        """Main execution loop."""
        if not os.getenv('OPENAI_API_KEY'):
            print("Error: OPENAI_API_KEY environment variable not set.")
            sys.exit(1)

        # Create new blip file
        blip_path = self.create_blip_file()
        print(f"Created blip: {blip_path}")

        # Initial edit
        if not self.edit_file(blip_path):
            print("No changes made. Canceling...")
            blip_path.unlink()
            return

        # Add initial version to stack
        self.version_stack.push(blip_path.read_text())

        # Main menu loop
        while True:
            choice = self.show_menu(blip_path)

            if choice == '1':  # Copyread
                self.copyread_blip(blip_path)
            elif choice == '2':  # Custom AI Processing
                self.custom_ai_processing(blip_path)
            elif choice == '3':  # Edit manually
                if self.edit_file(blip_path):
                    # User made changes, add to stack
                    self.version_stack.push(blip_path.read_text())
            elif choice == '4':  # Publish
                if self.deploy_blip():
                    print("Blog deployed successfully!")
                break
            elif choice == '5':  # Exit
                break
            elif choice == 'u':  # Undo
                self.undo_changes(blip_path)
            elif choice == 'r':  # Redo
                self.redo_changes(blip_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create and edit Hugo blip posts")
    parser.add_argument("project_root", help="Path to project root directory")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        print(f"Error: Project root {project_root} does not exist.")
        sys.exit(1)

    tool = BlipTool(project_root)
    tool.run()


if __name__ == "__main__":
    main()
