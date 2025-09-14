"""Interface for book content lookup services."""

from abc import ABC, abstractmethod
from typing import Optional
from models.book import Book


class ContentLookupInterface(ABC):
    """Abstract interface for looking up book metadata."""

    @abstractmethod
    async def lookup_by_isbn(self, isbn: str) -> Optional[Book]:
        """Look up book metadata by ISBN.

        Args:
            isbn: The ISBN of the book

        Returns:
            Book object with metadata or None if not found
        """
        pass
