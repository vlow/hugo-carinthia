#!/usr/bin/env python3
"""
Content Formatter

Formats markdown content to have one sentence per line while preserving paragraph structure.
This allows for better diff visualization when AI tools make changes to content.
"""

import re
import sys
from pathlib import Path
from typing import List


def format_content(content: str) -> str:
    """
    Format content to have one sentence per line while preserving paragraphs.

    Args:
        content: Original markdown content

    Returns:
        Formatted content with one sentence per line
    """
    # Split content into frontmatter and body
    frontmatter, body = parse_hugo_content(content)

    if not body.strip():
        return content

    # Split into paragraphs (separated by double newlines or more)
    paragraphs = re.split(r'\n\s*\n', body.strip())

    formatted_paragraphs = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue

        # Skip code blocks, headers, lists, etc.
        if should_skip_formatting(paragraph):
            formatted_paragraphs.append(paragraph)
            continue

        # Format regular paragraphs
        formatted_paragraph = format_paragraph(paragraph)
        formatted_paragraphs.append(formatted_paragraph)

    formatted_body = '\n\n'.join(formatted_paragraphs)

    # Reconstruct the full content
    if frontmatter:
        return f"{frontmatter}\n\n{formatted_body}"
    else:
        return formatted_body


def parse_hugo_content(content: str) -> tuple[str, str]:
    """Parse Hugo content into frontmatter and body."""
    content = content.strip()
    if not content.startswith('+++'):
        return '', content

    lines = content.split('\n')
    frontmatter_end = -1

    # Find end of frontmatter
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '+++':
            frontmatter_end = i
            break

    if frontmatter_end == -1:
        return '', content

    frontmatter_lines = lines[:frontmatter_end + 1]
    body_lines = lines[frontmatter_end + 1:]

    # Skip empty lines after frontmatter
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)

    frontmatter = '\n'.join(frontmatter_lines)
    body = '\n'.join(body_lines)

    return frontmatter, body


def should_skip_formatting(paragraph: str) -> bool:
    """Check if paragraph should skip sentence-per-line formatting."""
    stripped = paragraph.strip()

    # Skip headers
    if stripped.startswith('#'):
        return True

    # Skip code blocks
    if '```' in stripped:
        return True

    # Skip HTML blocks
    if stripped.startswith('<') and stripped.endswith('>'):
        return True

    # Skip lists
    if re.match(r'^\s*[-*+]\s', stripped) or re.match(r'^\s*\d+\.\s', stripped):
        return True

    # Skip blockquotes
    if stripped.startswith('>'):
        return True

    # Skip image/link lines
    if re.match(r'^\s*!\[.*?\]\(.*?\)\s*$', stripped):
        return True

    return False


def format_paragraph(paragraph: str) -> str:
    """Format a paragraph to have one sentence per line."""
    text = paragraph.strip()

    # Simple sentence splitting - this could be made more sophisticated
    # Split on sentence endings followed by whitespace
    sentences = re.split(r'([.!?]+)\s+', text)

    # Reconstruct sentences with proper endings
    formatted_sentences = []
    i = 0
    while i < len(sentences):
        sentence = sentences[i].strip()
        if not sentence:
            i += 1
            continue

        # Check if next element is punctuation
        if i + 1 < len(sentences) and re.match(r'^[.!?]+$', sentences[i + 1]):
            sentence += sentences[i + 1]
            i += 2
        else:
            i += 1

        if sentence:
            formatted_sentences.append(sentence)

    return '\n'.join(formatted_sentences)


def format_file(file_path: Path) -> bool:
    """
    Format a file in place.

    Args:
        file_path: Path to the markdown file

    Returns:
        True if file was modified, False otherwise
    """
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return False

    try:
        original_content = file_path.read_text(encoding='utf-8')
        formatted_content = format_content(original_content)

        if original_content != formatted_content:
            file_path.write_text(formatted_content, encoding='utf-8')
            print(f"Formatted: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False

    except Exception as e:
        print(f"Error formatting {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python format_content.py <markdown_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    success = format_file(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
