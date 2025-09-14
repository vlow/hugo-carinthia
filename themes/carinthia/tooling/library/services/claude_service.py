"""Anthropic Claude service implementation."""

import base64
import os
from pathlib import Path
from typing import Optional
import anthropic
from interfaces.llm_interface import LLMInterface
from models.book import Book


class ClaudeService(LLMInterface):
    """Anthropic Claude service for generating SVGs."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        if not os.getenv('ANTHROPIC_API_KEY'):
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    def _load_prompt_template(self, template_name: str) -> str:
        """Load prompt template from file."""
        template_path = Path(__file__).parent.parent / "prompts" / template_name
        return template_path.read_text().strip()

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """Encode image to base64 string and detect media type."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # Determine media type from file extension
        extension = Path(image_path).suffix.lower()
        media_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }.get(extension, 'image/jpeg')

        return image_data, media_type

    def _format_prompt(self, template: str, book: Book, cover_svg: str = None) -> str:
        """Format prompt template with book information."""
        format_dict = {
            'title': book.title or "Unknown Title",
            'author': book.author or "Unknown Author",
            'description': book.description or "No description available",
            'publication_year': book.publication_year or "Unknown"
        }

        if cover_svg is not None:
            format_dict['cover_svg'] = cover_svg

        return template.format(**format_dict)

    async def generate_cover_svg(self, cover_image_path: str, book: Book) -> str:
        """Generate a 236x327px cover SVG based on the original cover."""
        template = self._load_prompt_template("cover_svg_prompt.txt")
        prompt = self._format_prompt(template, book)

        # Encode the cover image
        base64_image, media_type = self._encode_image(cover_image_path)

        message = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        return message.content[0].text.strip()

    async def generate_banner_svg(self, cover_image_path: str, book: Book, cover_svg: str) -> str:
        """Generate a 1024x200px banner SVG based on the original cover and stylized SVG cover."""
        template = self._load_prompt_template("banner_svg_prompt.txt")
        prompt = self._format_prompt(template, book, cover_svg)

        # Encode the cover image
        base64_image, media_type = self._encode_image(cover_image_path)

        message = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        return message.content[0].text.strip()

    async def generate_cover_image(self, book: Book) -> Optional[str]:
        """Claude cannot generate images, so this returns None."""
        print("Claude does not support image generation. Skipping cover image generation.")
        return None
