"""Goodreads web scraper for content lookup."""

import aiohttp
from bs4 import BeautifulSoup
from typing import Optional
import re
from interfaces.content_lookup import ContentLookupInterface
from models.book import Book


class GoodreadsScraperService(ContentLookupInterface):
    """Goodreads web scraper service for looking up book metadata."""

    BASE_URL = "https://www.goodreads.com"

    async def lookup_by_isbn(self, isbn: str) -> Optional[Book]:
        """Look up book metadata by ISBN using Goodreads web scraping."""
        # Search URL for ISBN - Goodreads often redirects directly to book page
        search_url = f"{self.BASE_URL}/search?q={isbn}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # Search for the book (may redirect directly to book page)
                async with session.get(search_url) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Check if we were redirected directly to a book page
                    if '/book/show/' in str(response.url):
                        # We're already on the book page, extract metadata directly
                        return await self._extract_book_metadata(soup, isbn)
                    else:
                        # We're on search results page, find the first book
                        book_links = soup.select('a[href*="/book/show/"]')
                        if not book_links:
                            return None

                        # Get the first book link
                        book_url = book_links[0].get('href')
                        if not book_url.startswith('http'):
                            book_url = self.BASE_URL + book_url

                        # Get the book details page
                        async with session.get(book_url) as book_response:
                            if book_response.status != 200:
                                return None

                            book_html = await book_response.text()
                            book_soup = BeautifulSoup(book_html, 'html.parser')
                            return await self._extract_book_metadata(book_soup, isbn)

            except Exception as e:
                print(f"Error scraping Goodreads: {e}")
                return None

    async def _extract_book_metadata(self, soup: BeautifulSoup, isbn: str) -> Optional[Book]:
        """Extract book metadata from a Goodreads book page."""
        try:
            # Extract title - try multiple selectors
            title = ''
            title_selectors = ['h1[data-testid="bookTitle"]', 'h1.Text__title1', 'h1']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            # Extract author - try multiple selectors
            author = ''
            author_selectors = ['[data-testid="name"]', '.ContributorLink__name', 'a[href*="/author/show/"]']
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    break

            # Extract publication year - try multiple approaches
            pub_year = None
            pub_selectors = ['p[data-testid="publicationInfo"]', '.FeaturedDetails', '.BookPageMetadataSection__details']
            for selector in pub_selectors:
                details = soup.select(selector)
                for detail in details:
                    text = detail.get_text()
                    year_match = re.search(r'(\d{4})', text)
                    if year_match:
                        pub_year = int(year_match.group(1))
                        break
                if pub_year:
                    break

            # Extract page count - try multiple approaches
            pages = None
            page_selectors = ['p[data-testid="pagesFormat"]', '.FeaturedDetails', '.BookPageMetadataSection__details']
            for selector in page_selectors:
                page_info = soup.select(selector)
                for info in page_info:
                    text = info.get_text()
                    pages_match = re.search(r'(\d+)\s+pages', text)
                    if pages_match:
                        pages = int(pages_match.group(1))
                        break
                if pages:
                    break

            # Extract description - try multiple selectors
            description = ''
            desc_selectors = ['[data-testid="description"]', '.BookPageMetadataSection__description', '.expandableHtml']
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break

            if title and author:
                return Book(
                    isbn=isbn,
                    title=title,
                    author=author,
                    publication_year=pub_year,
                    pages=pages,
                    description=description
                )

            return None

        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return None
