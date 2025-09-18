"""OpenAI service implementation."""

import base64
import os
import sys
from pathlib import Path
from typing import Optional
import openai
from interfaces.llm_interface import LLMInterface
from models.book import Book

# Add parent directory to path to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.config import config_manager


class OpenAIService(LLMInterface):
    """OpenAI GPT-5 service for generating SVGs and cover images.

    Uses GPT-5 with reasoning capabilities and adjustable reasoning effort.
    """

    def __init__(self):
        api_key = config_manager.get_api_key('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required (set environment variable or add to ~/.config/carinthia/config.json)")

        self.client = openai.AsyncOpenAI(api_key=api_key)

    def _load_prompt_template(self, template_name: str) -> str:
        """Load prompt template from file."""
        template_path = Path(__file__).parent.parent / "prompts" / template_name
        return template_path.read_text().strip()

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

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

    def _clean_reasoning_output(self, response: str) -> str:
        """Clean GPT-5 reasoning output to extract only the final prompt."""
        # Remove thinking tags and reasoning content
        import re

        # Remove <thinking>...</thinking> blocks
        response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL)

        # Remove any remaining XML-like tags that might contain reasoning
        response = re.sub(r'<[^>]+>.*?</[^>]+>', '', response, flags=re.DOTALL)

        # Clean up extra whitespace and return clean prompt
        return response.strip()

    async def generate_cover_svg(self, cover_image_path: str, book: Book) -> str:
        """Generate a 236x327px cover SVG based on the original cover."""
        template = self._load_prompt_template("cover_svg_prompt.txt")
        prompt = self._format_prompt(template, book)

        # Encode the cover image
        base64_image = self._encode_image(cover_image_path)

        response = await self.client.chat.completions.create(
            model="gpt-5",  # o1-preview doesn't support vision yet, use latest GPT-4 with vision
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=16000,
            temperature=1,
            reasoning_effort="high"  # Use high reasoning effort for complex SVG generation
        )

        return response.choices[0].message.content.strip()

    async def generate_banner_svg(self, cover_image_path: str, book: Book, cover_svg: str) -> str:
        """Generate a 1024x200px banner SVG based on the original cover and stylized SVG cover."""
        template = self._load_prompt_template("banner_svg_prompt.txt")
        prompt = self._format_prompt(template, book, cover_svg)

        # Encode the cover image
        base64_image = self._encode_image(cover_image_path)

        response = await self.client.chat.completions.create(
            model="gpt-5",  # GPT-5 with reasoning capabilities
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=16000,
            temperature=1,
            reasoning_effort="high"  # Use high reasoning effort for complex SVG generation
        )

        return response.choices[0].message.content.strip()

    async def generate_cover_svg_direct(self, book: Book) -> str:
        """Generate a 236x327px cover SVG based solely on book text information."""
        template = self._load_prompt_template("direct_cover_svg_prompt.txt")
        prompt = self._format_prompt(template, book)

        response = await self.client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=16000,
            temperature=1,
            reasoning_effort="high"  # Use high reasoning effort for creative design decisions
        )

        return response.choices[0].message.content.strip()

    async def generate_banner_svg_direct(self, book: Book, cover_svg: str) -> str:
        """Generate a 1024x200px banner SVG based solely on the stylized SVG cover."""
        template = self._load_prompt_template("direct_banner_svg_prompt.txt")
        prompt = self._format_prompt(template, book, cover_svg)

        response = await self.client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=16000,
            temperature=1,
            reasoning_effort="high"  # Use high reasoning effort for creative design decisions
        )

        return response.choices[0].message.content.strip()

    async def generate_cover_image(self, book: Book) -> Optional[str]:
        """Generate an alternative cover image using GPT-5 enhanced prompts with DALL-E 3."""
        template = self._load_prompt_template("cover_generation_prompt.txt")
        base_prompt = self._format_prompt(template, book)

        try:
            # Use GPT-5 to enhance and refine the image generation prompt
            enhancement_template = self._load_prompt_template("image_enhancement_prompt.txt")
            enhancement_prompt = enhancement_template.format(base_prompt=base_prompt)

            enhanced_prompt_response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "user",
                        "content": enhancement_prompt
                    }
                ],
                max_completion_tokens=16000,
                temperature=1,
                reasoning_effort="medium"
            )

            enhanced_prompt = self._clean_reasoning_output(enhanced_prompt_response.choices[0].message.content)

            # Use the enhanced prompt for DALL-E 3 image generation
            response = await self.client.images.generate(
                model="dall-e-3",  # DALL-E 3 for image generation
                prompt=enhanced_prompt,
                size="1024x1792",
                quality="standard",
                n=1,
            )

            return response.data[0].url

        except Exception as e:
            print(f"Error generating cover image with GPT-5 + DALL-E 3: {e}")
            return None
