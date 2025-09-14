"""Interface for LLM services."""

from abc import ABC, abstractmethod
from typing import Optional
from models.book import Book


class LLMInterface(ABC):
    """Abstract interface for LLM services."""

    @abstractmethod
    async def generate_cover_svg(self, cover_image_path: str, book: Book) -> str:
        """Generate a 236x327px cover SVG based on the original cover.

        Args:
            cover_image_path: Path to the original cover image
            book: Book metadata

        Returns:
            SVG code as string
        """
        pass

    @abstractmethod
    async def generate_banner_svg(self, cover_image_path: str, book: Book, cover_svg: str) -> str:
        """Generate a 1024x200px banner SVG based on the original cover and stylized SVG cover.

        Args:
            cover_image_path: Path to the original cover image
            book: Book metadata
            cover_svg: The generated SVG cover code for consistency

        Returns:
            SVG code as string
        """
        pass

    @abstractmethod
    async def generate_cover_image(self, book: Book) -> Optional[str]:
        """Generate an alternative cover image using AI.

        Args:
            book: Book metadata

        Returns:
            URL to generated cover image or None if failed
        """
        pass
