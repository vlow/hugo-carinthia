"""Google Books cover lookup service."""

import aiohttp
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from interfaces.cover_lookup import CoverLookupInterface
from models.book import Book


class GoogleBooksCoverService(CoverLookupInterface):
    """Google Books API service for looking up and downloading book covers."""

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    async def get_cover_url(self, book: Book) -> Optional[str]:
        """Get cover image URL from Google Books API."""
        url = f"{self.BASE_URL}?q=isbn:{quote(book.isbn)}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

                    if not data.get('items'):
                        return None

                    # Get the first result
                    item = data['items'][0]
                    volume_info = item.get('volumeInfo', {})
                    image_links = volume_info.get('imageLinks', {})

                    # Try different image sizes, prefer larger ones
                    for size in ['extraLarge', 'large', 'medium', 'small', 'thumbnail']:
                        if size in image_links:
                            # Replace http with https for security
                            cover_url = image_links[size].replace('http://', 'https://')
                            return cover_url

                    return None

            except Exception as e:
                print(f"Error getting cover URL from Google Books: {e}")
                return None

    async def download_cover(self, book: Book) -> Optional[str]:
        """Download cover image to a temporary file."""
        cover_url = await self.get_cover_url(book)
        if not cover_url:
            return None

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(cover_url) as response:
                    if response.status != 200:
                        return None

                    # Create temporary file
                    suffix = '.jpg'  # Google Books typically serves JPEG
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                        content = await response.read()
                        tmp_file.write(content)
                        print(f"Google Books cover downloaded to: {tmp_file.name}")
                        return tmp_file.name

            except Exception as e:
                print(f"Error downloading cover from Google Books: {e}")
                return None
