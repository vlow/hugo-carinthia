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
        """Look up book metadata trying each service and merging results."""
        google_books_result = None
        goodreads_result = None

        for service in self.services:
            try:
                book = await service.lookup_by_isbn(isbn)
                if book:
                    if isinstance(service, GoogleBooksService):
                        google_books_result = book
                    elif isinstance(service, GoodreadsScraperService):
                        goodreads_result = book
            except Exception as e:
                print(f"Error with {service.__class__.__name__}: {e}")
                continue

        # Merge results, prioritizing Google Books but filling missing data from Goodreads
        if google_books_result:
            merged_book = google_books_result
            if goodreads_result:
                # Fill in missing page count from Goodreads
                if not merged_book.pages and goodreads_result.pages:
                    merged_book.pages = goodreads_result.pages
                # Fill in missing description from Goodreads
                if not merged_book.description and goodreads_result.description:
                    merged_book.description = goodreads_result.description
            return merged_book
        elif goodreads_result:
            return goodreads_result

        return None
