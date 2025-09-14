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
import sys
import tempfile
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

            # Get full absolute path
            full_path = os.path.abspath(filename)
            pairs[hash_prefix][file_type] = full_path

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

                        print(f"Generated cover downloaded to temporary file")
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
                           overflow_fixer: SimpleOverflowFixer, generation_id: int) -> List[str]:
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

        with open(cover_filename, 'w') as f:
            f.write(corrected_cover_svg)
        print(f"Generation {generation_id}: Generated {cover_filename}")
        generated_files.append(cover_filename)

        # Generate banner image (1024x200px) based on corrected cover SVG
        banner_svg = await llm_service.generate_banner_svg(cover_path, book, corrected_cover_svg)

        # Apply minimal overflow fixes if needed
        corrected_banner_svg = overflow_fixer.fix_overflow(banner_svg, 'banner')
        banner_filename = f"{random_hash}_{book.isbn}_banner{model_suffix}_{timestamp}.svg"

        with open(banner_filename, 'w') as f:
            f.write(corrected_banner_svg)
        print(f"Generation {generation_id}: Generated {banner_filename}")
        generated_files.append(banner_filename)

    return generated_files


async def generate_svg_pair_direct(book: Book, models: List[str],
                                  overflow_fixer: SimpleOverflowFixer, generation_id: int) -> List[str]:
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

        with open(cover_filename, 'w') as f:
            f.write(corrected_cover_svg)
        print(f"Generation {generation_id}: Generated {cover_filename}")
        generated_files.append(cover_filename)

        # Generate banner image (1024x200px) based on corrected cover SVG only
        banner_svg = await llm_service.generate_banner_svg_direct(book, corrected_cover_svg)

        # Apply minimal overflow fixes if needed
        corrected_banner_svg = overflow_fixer.fix_overflow(banner_svg, 'banner')
        banner_filename = f"{random_hash}_{book.isbn}_banner{model_suffix}_{timestamp}.svg"

        with open(banner_filename, 'w') as f:
            f.write(corrected_banner_svg)
        print(f"Generation {generation_id}: Generated {banner_filename}")
        generated_files.append(banner_filename)

    return generated_files


async def main():
    parser = argparse.ArgumentParser(description='Generate library images from ISBN')
    parser.add_argument('isbn', help='ISBN of the book')
    parser.add_argument('--model', choices=['gpt-5', 'claude'],
                       help='LLM model to use (can be specified multiple times)',
                       action='append')
    parser.add_argument('-n', '--parallel', type=int, default=1,
                       help='Number of parallel generations to create (default: 1)')
    parser.add_argument('-g', '--generate-cover', action='store_true',
                       help='Use LLM-generated cover image instead of downloading original cover')
    parser.add_argument('-d', '--direct', action='store_true',
                       help='Generate SVGs directly from book description without any cover image')

    args = parser.parse_args()

    if not args.model:
        args.model = ['gpt-5']

    # Validate conflicting flags
    if args.generate_cover and args.direct:
        print("Error: Cannot use both --generate-cover (-g) and --direct (-d) flags together")
        sys.exit(1)

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

        if args.direct:
            # Direct mode - generate SVGs from text only
            print("Using direct mode - generating SVGs from text only...")

            # Create parallel generation tasks for direct mode
            print(f"Starting {args.parallel} parallel direct generations...")
            tasks = []
            for i in range(args.parallel):
                task = generate_svg_pair_direct(book, args.model, overflow_fixer, i + 1)
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
                task = generate_svg_pair(book, cover_path, args.model, overflow_fixer, i + 1)
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

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
