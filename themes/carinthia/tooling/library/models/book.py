"""Book model for library image generation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Book:
    """Book metadata model."""
    isbn: str
    title: str
    author: str
    publication_year: Optional[int] = None
    pages: Optional[int] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert book to dictionary for JSON output."""
        return {
            'isbn': self.isbn,
            'title': self.title,
            'author': self.author,
            'publication_year': self.publication_year,
            'pages': self.pages,
            'description': self.description
        }
