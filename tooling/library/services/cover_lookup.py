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
        # Try non-AI sources first
        non_ai_services = [s for s in self.services if not isinstance(s, AICoverGeneratorService)]
        ai_services = [s for s in self.services if isinstance(s, AICoverGeneratorService)]

        # First try all non-AI sources
        for service in non_ai_services:
            try:
                cover_path = await service.download_cover(book)
                if cover_path:
                    return cover_path
            except Exception as e:
                print(f"Error with {service.__class__.__name__}: {e}")
                continue

        # If no cover found from regular sources, inform user and try AI generation
        if ai_services:
            print("No cover image found from available sources (Google Books, Goodreads).")
            print("Generating AI cover image as fallback...")

            for service in ai_services:
                try:
                    cover_path = await service.download_cover(book)
                    if cover_path:
                        return cover_path
                except Exception as e:
                    print(f"Error with {service.__class__.__name__}: {e}")
                    continue

            # If AI fallback failed, suggest --direct mode
            print("Failed to generate AI cover image as fallback.")
            print("Tip: Use the -d/--direct flag to skip cover image generation and create vector graphics directly from text.")
        else:
            # No AI services available at all
            print("No cover image found from available sources (Google Books, Goodreads).")
            print("AI cover generation is not available (missing OPENAI_API_KEY).")
            print("Tip: Use the -d/--direct flag to skip cover image generation and create vector graphics directly from text.")

        return None
