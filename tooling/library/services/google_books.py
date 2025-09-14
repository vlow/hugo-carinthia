"""Google Books API implementation for content lookup."""

import aiohttp
from typing import Optional
from urllib.parse import quote
from interfaces.content_lookup import ContentLookupInterface
from models.book import Book


class GoogleBooksService(ContentLookupInterface):
    """Google Books API service for looking up book metadata."""

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    async def lookup_by_isbn(self, isbn: str) -> Optional[Book]:
        """Look up book metadata by ISBN using Google Books API."""
        url = f"{self.BASE_URL}?q=isbn:{quote(isbn)}"

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

                    # Extract metadata
                    title = volume_info.get('title', '')
                    authors = volume_info.get('authors', [])
                    author = ', '.join(authors) if authors else ''

                    # Parse publication date (could be year only or full date)
                    pub_date = volume_info.get('publishedDate', '')
                    pub_year = None
                    if pub_date:
                        try:
                            pub_year = int(pub_date.split('-')[0])
                        except (ValueError, IndexError):
                            pass

                    pages = volume_info.get('pageCount')
                    description = volume_info.get('description', '')

                    return Book(
                        isbn=isbn,
                        title=title,
                        author=author,
                        publication_year=pub_year,
                        pages=pages,
                        description=description
                    )

            except Exception as e:
                print(f"Error fetching from Google Books: {e}")
                return None
