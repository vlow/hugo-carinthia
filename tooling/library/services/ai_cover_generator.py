"""AI-generated cover service as fallback."""

import aiohttp
import tempfile
import base64
from typing import Optional
from interfaces.cover_lookup import CoverLookupInterface
from interfaces.llm_interface import LLMInterface
from models.book import Book


class AICoverGeneratorService(CoverLookupInterface):
    """AI-powered cover generator service as fallback when no cover is found."""

    def __init__(self, llm_service: LLMInterface):
        self.llm_service = llm_service

    async def get_cover_url(self, book: Book) -> Optional[str]:
        """Generate cover image URL using AI."""
        return await self.llm_service.generate_cover_image(book)

    async def download_cover(self, book: Book) -> Optional[str]:
        """Generate and download AI cover image to a temporary file."""
        try:
            # Use the LLM service to generate a cover image
            image_url = await self.llm_service.generate_cover_image(book)
            if not image_url:
                return None

            # Download the generated image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return None

                    # Create temporary file
                    suffix = '.png'  # AI-generated images are typically PNG
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                        content = await response.read()
                        tmp_file.write(content)
                        return tmp_file.name

        except Exception as e:
            print(f"Error generating AI cover: {e}")
            return None
