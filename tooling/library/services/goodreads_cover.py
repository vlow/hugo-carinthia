"""Goodreads cover lookup service."""

import aiohttp
import tempfile
from bs4 import BeautifulSoup
from typing import Optional
from interfaces.cover_lookup import CoverLookupInterface
from models.book import Book


class GoodreadsCoverService(CoverLookupInterface):
    """Goodreads web scraper service for looking up and downloading book covers."""

    BASE_URL = "https://www.goodreads.com"

    async def get_cover_url(self, book: Book) -> Optional[str]:
        """Get cover image URL from Goodreads by scraping."""
        search_url = f"{self.BASE_URL}/search?q={book.isbn}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # Search for the book
                async with session.get(search_url) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Find the first book result and its cover
                    book_cover = soup.select_one('img.bookCover')
                    if book_cover:
                        cover_url = book_cover.get('src')
                        if cover_url and not cover_url.startswith('data:'):
                            # Replace small covers with larger ones if possible
                            if '_SX' in cover_url:
                                cover_url = cover_url.replace('_SX98_', '_SX318_')
                                cover_url = cover_url.replace('_SY160_', '_SY475_')
                            return cover_url

                    return None

            except Exception as e:
                print(f"Error getting cover URL from Goodreads: {e}")
                return None

    async def download_cover(self, book: Book) -> Optional[str]:
        """Download cover image to a temporary file."""
        cover_url = await self.get_cover_url(book)
        if not cover_url:
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(cover_url) as response:
                    if response.status != 200:
                        return None

                    # Determine file extension from URL or content type
                    suffix = '.jpg'
                    if cover_url.endswith('.png'):
                        suffix = '.png'
                    elif 'content-type' in response.headers:
                        content_type = response.headers['content-type']
                        if 'png' in content_type:
                            suffix = '.png'

                    # Create temporary file
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                        content = await response.read()
                        tmp_file.write(content)
                        return tmp_file.name

            except Exception as e:
                print(f"Error downloading cover from Goodreads: {e}")
                return None
