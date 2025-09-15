#!/usr/bin/env python3
"""
Library Image Generator Tool

A tool to generate SVG cover and banner images for books in a Hugo library.
Takes an ISBN as input and creates themed SVG images using multimodal LLMs.
"""

import argparse
import asyncio
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

import aiohttp

from services.content_lookup import ContentLookupService
from services.cover_lookup import CoverLookupService
from services.llm_service import LLMService
from services.simple_overflow_fixer import SimpleOverflowFixer
from models.book import Book


def group_files_by_pairs(generated_files: List[str]) -> Dict:
    """Group generated SVG files by their hash prefix to create cover/banner pairs."""
    pairs = {}

    for filename in generated_files:
        # Extract hash from filename (format: hash_isbn_type[_model]_timestamp.svg)
        # The hash is always the first part before the first underscore
        if '_' in filename:
            hash_prefix = filename.split('_')[0]

            # Determine if this is a cover or banner
            if '_cover' in filename:
                file_type = 'cover'
            elif '_banner' in filename:
                file_type = 'banner'
            else:
                continue

            # Initialize pair if not exists
            if hash_prefix not in pairs:
                pairs[hash_prefix] = {
                    'hash': hash_prefix,
                    'cover': None,
                    'banner': None
                }

            # Store just the filename - files are in output_dir
            pairs[hash_prefix][file_type] = filename

    # Convert to list and filter out incomplete pairs
    paired_files = []
    for pair in pairs.values():
        if pair['cover'] and pair['banner']:
            paired_files.append(pair)

    return {
        'generated_files': paired_files
    }


async def generate_and_download_cover(book: Book, models: List[str]) -> Optional[str]:
    """Generate a cover image using LLM and download it to a temporary file."""
    # Try each model until one succeeds in generating an image
    for model in models:
        try:
            llm_service = LLMService.create(model)
            print(f"Generating cover image using {model}...")

            # Generate cover image URL
            cover_url = await llm_service.generate_cover_image(book)
            if not cover_url:
                print(f"{model} does not support cover image generation")
                continue

            print(f"Downloading generated cover from {model}...")

            # Download the generated image
            async with aiohttp.ClientSession() as session:
                async with session.get(cover_url) as response:
                    if response.status == 200:
                        # Create temporary file
                        suffix = '.jpg'  # Most AI-generated images are JPEG
                        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)

                        # Write image data to temp file
                        with open(temp_fd, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        print(f"AI cover downloaded to: {temp_path}")
                        return temp_path
                    else:
                        print(f"Failed to download generated cover (status: {response.status})")
                        continue

        except Exception as e:
            print(f"Error generating cover with {model}: {e}")
            continue

    print("Failed to generate cover image with any available model")
    return None


async def generate_svg_pair(book: Book, cover_path: str, models: List[str],
                           overflow_fixer: SimpleOverflowFixer, generation_id: int, output_dir: str = ".") -> List[str]:
    """Generate one complete set of SVG files for all specified models."""
    # Generate unique timestamp and hash for this generation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_hash = secrets.token_hex(2)

    generated_files = []
    llm_services = [LLMService.create(model) for model in models]

    for i, llm_service in enumerate(llm_services):
        model_suffix = f"_{models[i]}" if len(models) > 1 else ""

        print(f"Generation {generation_id}: Generating images with {models[i]}...")

        # Generate cover image (236x327px)
        cover_svg = await llm_service.generate_cover_svg(cover_path, book)

        # Apply minimal overflow fixes if needed
        corrected_cover_svg = overflow_fixer.fix_overflow(cover_svg, 'cover')
        cover_filename = f"{random_hash}_{book.isbn}_cover{model_suffix}_{timestamp}.svg"
        cover_filepath = os.path.join(output_dir, cover_filename)

        with open(cover_filepath, 'w') as f:
            f.write(corrected_cover_svg)
        print(f"Generation {generation_id}: Generated {cover_filename}")
        generated_files.append(cover_filename)

        # Generate banner image (1024x200px) based on corrected cover SVG
        banner_svg = await llm_service.generate_banner_svg(cover_path, book, corrected_cover_svg)

        # Apply minimal overflow fixes if needed
        corrected_banner_svg = overflow_fixer.fix_overflow(banner_svg, 'banner')
        banner_filename = f"{random_hash}_{book.isbn}_banner{model_suffix}_{timestamp}.svg"
        banner_filepath = os.path.join(output_dir, banner_filename)

        with open(banner_filepath, 'w') as f:
            f.write(corrected_banner_svg)
        print(f"Generation {generation_id}: Generated {banner_filename}")
        generated_files.append(banner_filename)

    return generated_files


async def generate_svg_pair_direct(book: Book, models: List[str],
                                  overflow_fixer: SimpleOverflowFixer, generation_id: int, output_dir: str = ".") -> List[str]:
    """Generate one complete set of SVG files using direct text-only generation."""
    # Generate unique timestamp and hash for this generation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_hash = secrets.token_hex(2)

    generated_files = []
    llm_services = [LLMService.create(model) for model in models]

    for i, llm_service in enumerate(llm_services):
        model_suffix = f"_{models[i]}" if len(models) > 1 else ""

        print(f"Generation {generation_id}: Generating images with {models[i]} (direct mode)...")

        # Generate cover image (236x327px) directly from text
        cover_svg = await llm_service.generate_cover_svg_direct(book)

        # Apply minimal overflow fixes if needed
        corrected_cover_svg = overflow_fixer.fix_overflow(cover_svg, 'cover')
        cover_filename = f"{random_hash}_{book.isbn}_cover{model_suffix}_{timestamp}.svg"
        cover_filepath = os.path.join(output_dir, cover_filename)

        with open(cover_filepath, 'w') as f:
            f.write(corrected_cover_svg)
        print(f"Generation {generation_id}: Generated {cover_filename}")
        generated_files.append(cover_filename)

        # Generate banner image (1024x200px) based on corrected cover SVG only
        banner_svg = await llm_service.generate_banner_svg_direct(book, corrected_cover_svg)

        # Apply minimal overflow fixes if needed
        corrected_banner_svg = overflow_fixer.fix_overflow(banner_svg, 'banner')
        banner_filename = f"{random_hash}_{book.isbn}_banner{model_suffix}_{timestamp}.svg"
        banner_filepath = os.path.join(output_dir, banner_filename)

        with open(banner_filepath, 'w') as f:
            f.write(corrected_banner_svg)
        print(f"Generation {generation_id}: Generated {banner_filename}")
        generated_files.append(banner_filename)

    return generated_files


async def create_hugo_post(book: Book, post_dir: str) -> None:
    """Create a Hugo library post with prefilled frontmatter."""
    from datetime import datetime
    import slugify

    # Use index.md for page bundle (leaf bundle)
    post_filename = "index.md"
    post_path = os.path.join(post_dir, post_filename)

    # Generate current timestamp
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Determine category based on book metadata
    category = 'fiction'  # Default, could be enhanced with genre detection

    # Create frontmatter (no image paths needed - templates will find cover.svg and banner.svg automatically)
    frontmatter = f"""+++
title = '{book.title}'
date = {current_time}
draft = true
category = '{category}'
finished_date = {current_time}
pages = {book.pages or 0}
average_reading_time = '{int((book.pages or 0) / 35) if book.pages else 0}'
isbn = '{book.isbn}'
summary = ''
tags = []
+++

## About {book.title}

{book.description or "No description available."}

## My Thoughts

(Add your thoughts and review here)
"""

    # Write the post file
    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

    print(f"Created Hugo post: {post_path}")


async def handle_image_selection(paired_files_json: Dict, bundle_dir: str, all_generated_files: List[str], output_dir: str) -> None:
    """Handle user selection of images and move them to page bundle."""
    import shutil

    generated_pairs = paired_files_json.get('generated_files', [])

    if not generated_pairs:
        print("No complete cover/banner pairs were generated.")
        return

    print(f"\nGenerated {len(generated_pairs)} complete cover/banner pairs:")
    for i, pair in enumerate(generated_pairs, 1):
        cover_file = os.path.basename(pair['cover'])
        banner_file = os.path.basename(pair['banner'])
        print(f"{i}. Cover: {cover_file}")
        print(f"   Banner: {banner_file}")

    # Get user selection
    while True:
        try:
            choice = input(f"\nSelect which pair to use (1-{len(generated_pairs)}): ").strip()
            selected_index = int(choice) - 1
            if 0 <= selected_index < len(generated_pairs):
                break
            else:
                print(f"Please enter a number between 1 and {len(generated_pairs)}")
        except ValueError:
            print("Please enter a valid number")

    selected_pair = generated_pairs[selected_index]

    # Move selected images to page bundle directory
    cover_filename = selected_pair['cover']
    banner_filename = selected_pair['banner']

    # Construct full paths from output directory
    cover_src = os.path.join(output_dir, cover_filename)
    banner_src = os.path.join(output_dir, banner_filename)

    cover_dest = os.path.join(bundle_dir, 'cover.svg')
    banner_dest = os.path.join(bundle_dir, 'banner.svg')

    shutil.move(cover_src, cover_dest)
    shutil.move(banner_src, banner_dest)

    print(f"\nMoved selected images to page bundle:")
    print(f"  Cover: {cover_dest}")
    print(f"  Banner: {banner_dest}")

    # Clean up remaining generated files
    for filename in all_generated_files:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  Removed: {filename}")

    print("\nPage bundle setup complete!")


def launch_editor_for_post(post_path: str) -> None:
    """Launch editor for the created post with blocking detection."""
    # Get editor with fallback chain
    hugo_editor = os.getenv('HUGO_EDITOR')
    if not hugo_editor:
        hugo_editor = os.getenv('EDITOR')
    if not hugo_editor:
        hugo_editor = 'zed'

    # Check if the editor exists
    try:
        # Check if command exists (works for both PATH commands and full paths)
        result = subprocess.run(['which', hugo_editor], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️  Editor '{hugo_editor}' not found in PATH.")
            print("   Set HUGO_EDITOR or EDITOR environment variable to your preferred editor.")
            print("   Skipping editor launch.")
            return
    except Exception:
        print(f"⚠️  Could not verify editor '{hugo_editor}' exists.")
        print("   Skipping editor launch.")
        return

    print(f"\nOpening {hugo_editor} for editing...")
    print(f"Post location: {post_path}")
    print("")

    # Launch editor and measure time
    start_time = time.time()
    try:
        subprocess.run([hugo_editor, post_path])
    except Exception as e:
        print(f"⚠️  Failed to launch editor: {e}")
        return

    end_time = time.time()
    duration = int(end_time - start_time)

    # Provide feedback based on editor behavior
    if duration > 2:
        print("")
        print(f"⚠️  Editor took {duration} seconds to return.")
        if duration > 10:
            print("   Looks like you spent time editing - great!")
            print("   Note: Image generation was delayed while editing.")
        else:
            print("   This suggests a terminal editor that blocked image generation.")
        print("   Consider using a GUI editor (code, zed, gvim) for immediate detaching.")
        print("   Set HUGO_EDITOR environment variable to your preferred editor.")
        print("")


async def main():
    parser = argparse.ArgumentParser(description='Generate library images from ISBN')
    parser.add_argument('isbn', help='ISBN of the book')
    parser.add_argument('--model', choices=['gpt-5', 'claude'],
                       help='LLM model to use (can be specified multiple times)',
                       action='append')
    parser.add_argument('-n', '--parallel', type=int, default=8,
                       help='Number of parallel generations to create (default: 8)')
    parser.add_argument('-g', '--generate-cover', action='store_true',
                       help='Use LLM-generated cover image instead of downloading original cover')
    parser.add_argument('-d', '--direct', action='store_true',
                       help='Generate SVGs directly from book description without any cover image')
    parser.add_argument('-c', '--create', type=str, metavar='PATH',
                       help='Create post directory structure in the specified path')
    parser.add_argument('-e', '--edit', action='store_true',
                       help='Open post in editor after creation (requires --create)')

    args = parser.parse_args()

    if not args.model:
        args.model = ['gpt-5']

    # Validate conflicting flags
    if args.generate_cover and args.direct:
        print("Error: Cannot use both --generate-cover (-g) and --direct (-d) flags together")
        sys.exit(1)

    if args.edit and not args.create:
        print("Error: --edit (-e) requires --create (-c) flag")
        sys.exit(1)

    # Handle --create parameter
    output_dir = "."  # Default to current directory
    if args.create:
        # Check if the provided path exists
        if not os.path.isdir(args.create):
            print(f"Error: Directory '{args.create}' does not exist")
            sys.exit(1)

        # Normalize ISBN by removing dashes
        normalized_isbn = args.isbn.replace('-', '')

        # Create subdirectory with normalized ISBN
        isbn_dir = os.path.join(args.create, normalized_isbn)

        # Check if directory already exists
        if os.path.exists(isbn_dir):
            print(f"Error: Directory '{isbn_dir}' already exists")
            sys.exit(1)

        os.makedirs(isbn_dir)
        output_dir = isbn_dir
        print(f"Created directory: {isbn_dir}")

    try:
        # Initialize services
        content_service = ContentLookupService()
        cover_service = CoverLookupService()
        overflow_fixer = SimpleOverflowFixer()

        # Look up book metadata
        print(f"Looking up book metadata for ISBN: {args.isbn}")
        book = await content_service.lookup(args.isbn)

        if not book:
            print(f"Could not find book information for ISBN: {args.isbn}")
            sys.exit(1)

        print(f"Found: {book.title} by {book.author}")

        # Create Hugo library post if we're in creation mode
        if args.create:
            await create_hugo_post(book, isbn_dir)

            # Launch editor if requested
            if args.edit:
                post_file = os.path.join(isbn_dir, 'index.md')
                launch_editor_for_post(post_file)

        if args.direct:
            # Direct mode - generate SVGs from text only
            print("Using direct mode - generating SVGs from text only...")

            # Create parallel generation tasks for direct mode
            print(f"Starting {args.parallel} parallel direct generations...")
            tasks = []
            for i in range(args.parallel):
                task = generate_svg_pair_direct(book, args.model, overflow_fixer, i + 1, output_dir)
                tasks.append(task)

            # Run all generations in parallel
            all_generated_files = await asyncio.gather(*tasks)

        else:
            # Standard mode - use cover images
            # Get cover image - either download original or generate new one
            if args.generate_cover:
                print("Generating cover image with LLM...")
                cover_path = await generate_and_download_cover(book, args.model)
            else:
                print("Downloading original cover image...")
                cover_path = await cover_service.download_cover(book)

            if not cover_path:
                action = "generate" if args.generate_cover else "download"
                print(f"Could not {action} cover image")
                sys.exit(1)

            # Create parallel generation tasks
            print(f"Starting {args.parallel} parallel generations...")
            tasks = []
            for i in range(args.parallel):
                task = generate_svg_pair(book, cover_path, args.model, overflow_fixer, i + 1, output_dir)
                tasks.append(task)

            # Run all generations in parallel
            all_generated_files = await asyncio.gather(*tasks)

            # Clean up temporary cover file (whether downloaded or generated)
            if cover_path and Path(cover_path).exists():
                Path(cover_path).unlink()
                action = "Generated" if args.generate_cover else "Downloaded"
                print(f"{action} cover file cleaned up")

        # Flatten the list of lists
        generated_files = []
        for file_list in all_generated_files:
            generated_files.extend(file_list)

        mode_text = "direct " if args.direct else ""
        print(f"\nCompleted {args.parallel} {mode_text}generations:")
        for filename in generated_files:
            print(f"  {filename}")

        # Output book metadata as JSON
        book_json = book.to_dict()
        print(json.dumps(book_json, indent=2))

        # Output paired SVG files as second JSON
        paired_files_json = group_files_by_pairs(generated_files)
        print(json.dumps(paired_files_json, indent=2))

        # Handle image selection and cleanup if in creation mode
        if args.create:
            await handle_image_selection(paired_files_json, isbn_dir, generated_files, output_dir)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
