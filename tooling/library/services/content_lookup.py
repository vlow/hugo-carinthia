"""Content lookup service that tries multiple sources."""

from typing import Optional, List
from interfaces.content_lookup import ContentLookupInterface
from services.google_books import GoogleBooksService
from services.goodreads_scraper import GoodreadsScraperService
from models.book import Book


class ContentLookupService:
    """Service that tries multiple content lookup sources in order."""

    def __init__(self):
        self.services: List[ContentLookupInterface] = [
            GoogleBooksService(),
            GoodreadsScraperService()
        ]

    async def lookup(self, isbn: str) -> Optional[Book]:
        """Look up book metadata trying each service in order until one succeeds."""
        for service in self.services:
            try:
                book = await service.lookup_by_isbn(isbn)
                if book:
                    return book
            except Exception as e:
                print(f"Error with {service.__class__.__name__}: {e}")
                continue

        return None
