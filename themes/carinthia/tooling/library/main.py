#!/usr/bin/env python3
"""
Library Image Generator Tool

A tool to generate SVG cover and banner images for books in a Hugo library.
Takes an ISBN as input and creates themed SVG images using multimodal LLMs.
"""

import argparse
import asyncio
import json
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from services.content_lookup import ContentLookupService
from services.cover_lookup import CoverLookupService
from services.llm_service import LLMService
from services.simple_overflow_fixer import SimpleOverflowFixer
from models.book import Book


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


async def main():
    parser = argparse.ArgumentParser(description='Generate library images from ISBN')
    parser.add_argument('isbn', help='ISBN of the book')
    parser.add_argument('--model', choices=['gpt-5', 'claude'],
                       help='LLM model to use (can be specified multiple times)',
                       action='append')
    parser.add_argument('-n', '--parallel', type=int, default=1,
                       help='Number of parallel generations to create (default: 1)')

    args = parser.parse_args()

    if not args.model:
        args.model = ['gpt-5']

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

        # Download cover image
        print("Downloading cover image...")
        cover_path = await cover_service.download_cover(book)

        if not cover_path:
            print("Could not download cover image")
            sys.exit(1)

        # Create parallel generation tasks
        print(f"Starting {args.parallel} parallel generations...")
        tasks = []
        for i in range(args.parallel):
            task = generate_svg_pair(book, cover_path, args.model, overflow_fixer, i + 1)
            tasks.append(task)

        # Run all generations in parallel
        all_generated_files = await asyncio.gather(*tasks)

        # Flatten the list of lists
        generated_files = []
        for file_list in all_generated_files:
            generated_files.extend(file_list)

        print(f"\nCompleted {args.parallel} generations:")
        for filename in generated_files:
            print(f"  {filename}")

        # Output book metadata as JSON
        book_json = book.to_dict()
        print(json.dumps(book_json, indent=2))

        # Clean up temporary cover file
        if cover_path and Path(cover_path).exists():
            Path(cover_path).unlink()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
