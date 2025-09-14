"""Interface for book cover lookup services."""

from abc import ABC, abstractmethod
from typing import Optional
from models.book import Book


class CoverLookupInterface(ABC):
    """Abstract interface for looking up and downloading book covers."""

    @abstractmethod
    async def get_cover_url(self, book: Book) -> Optional[str]:
        """Get cover image URL for a book.

        Args:
            book: Book object with metadata

        Returns:
            URL to cover image or None if not found
        """
        pass

    @abstractmethod
    async def download_cover(self, book: Book) -> Optional[str]:
        """Download cover image and return path to temporary file.

        Args:
            book: Book object with metadata

        Returns:
            Path to downloaded cover image file or None if failed
        """
        pass
