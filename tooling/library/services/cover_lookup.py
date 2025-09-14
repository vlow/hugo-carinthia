"""Cover lookup service that tries multiple sources."""

from typing import Optional, List
from interfaces.cover_lookup import CoverLookupInterface
from services.google_books_cover import GoogleBooksCoverService
from services.goodreads_cover import GoodreadsCoverService
from services.ai_cover_generator import AICoverGeneratorService
from services.openai_service import OpenAIService
from models.book import Book


class CoverLookupService:
    """Service that tries multiple cover lookup sources in order."""

    def __init__(self):
        # Initialize services - AI generator will be added as fallback
        self.services: List[CoverLookupInterface] = [
            GoogleBooksCoverService(),
            GoodreadsCoverService()
        ]

        # Add AI cover generator as fallback
        try:
            ai_service = OpenAIService()
            self.services.append(AICoverGeneratorService(ai_service))
        except Exception as e:
            print(f"Could not initialize AI cover generator: {e}")

    async def download_cover(self, book: Book) -> Optional[str]:
        """Download cover image trying each service in order until one succeeds."""
        for service in self.services:
            try:
                cover_path = await service.download_cover(book)
                if cover_path:
                    return cover_path
            except Exception as e:
                print(f"Error with {service.__class__.__name__}: {e}")
                continue

        return None
