#!/usr/bin/env python3
"""
Library Image Generator Tool

A tool to generate SVG cover and banner images for books in a Hugo library.
Takes an ISBN as input and creates themed SVG images using multimodal LLMs.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from services.content_lookup import ContentLookupService
from services.cover_lookup import CoverLookupService
from services.llm_service import LLMService
from models.book import Book


async def main():
    parser = argparse.ArgumentParser(description='Generate library images from ISBN')
    parser.add_argument('isbn', help='ISBN of the book')
    parser.add_argument('--model', choices=['gpt-5', 'claude'],
                       help='LLM model to use (can be specified multiple times)',
                       action='append')

    args = parser.parse_args()

    if not args.model:
        args.model = ['gpt-5']

    try:
        # Initialize services
        content_service = ContentLookupService()
        cover_service = CoverLookupService()
        llm_services = [LLMService.create(model) for model in args.model]

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

        # Generate SVG images using each LLM
        for i, llm_service in enumerate(llm_services):
            model_suffix = f"_{args.model[i]}" if len(args.model) > 1 else ""

            print(f"Generating images with {args.model[i]}...")

            # Generate cover image (236x327px)
            cover_svg = await llm_service.generate_cover_svg(cover_path, book)
            cover_filename = f"{book.isbn}_cover{model_suffix}.svg"

            with open(cover_filename, 'w') as f:
                f.write(cover_svg)
            print(f"Generated: {cover_filename}")

            # Generate banner image (1024x200px)
            banner_svg = await llm_service.generate_banner_svg(cover_path, book)
            banner_filename = f"{book.isbn}_banner{model_suffix}.svg"

            with open(banner_filename, 'w') as f:
                f.write(banner_svg)
            print(f"Generated: {banner_filename}")

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
