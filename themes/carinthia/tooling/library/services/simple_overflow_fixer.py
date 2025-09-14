"""Simple SVG text overflow detection and correction."""

import re
from typing import Optional


class SimpleOverflowFixer:
    """Minimal SVG text overflow correction service."""

    def __init__(self):
        # Character width estimation (conservative)
        self.avg_char_width = 0.7  # Average character width relative to font size

    def fix_overflow(self, svg_content: str, svg_type: str = 'cover') -> str:
        """Apply minimal fixes only if text appears to overflow.

        Args:
            svg_content: The SVG content as string
            svg_type: Either 'cover' or 'banner'

        Returns:
            Corrected SVG content (or original if no fixes needed)
        """
        try:
            if svg_type == 'banner':
                width = 1024
                safe_margin = 10
            else:  # cover
                width = 236
                safe_margin = 10

            corrected_svg = svg_content
            fixes_applied = False

            # Find text elements that might be problematic
            text_elements = self._find_text_elements(svg_content)

            for match in text_elements:
                if self._appears_to_overflow(match, width, safe_margin):
                    fixed_element = self._apply_minimal_fix(match, width, safe_margin)
                    if fixed_element != match.group(0):
                        corrected_svg = corrected_svg.replace(match.group(0), fixed_element)
                        fixes_applied = True

            if fixes_applied:
                print(f"Applied minimal overflow fixes to {svg_type}")

            return corrected_svg

        except Exception as e:
            print(f"Error in overflow fixer: {e}")
            return svg_content

    def _find_text_elements(self, svg_content: str) -> list:
        """Find text elements that might need fixing."""
        # Pattern to match text elements with their attributes
        pattern = r'<text[^>]*>.*?</text>'
        return list(re.finditer(pattern, svg_content, re.DOTALL))

    def _appears_to_overflow(self, text_match, canvas_width: int, margin: int) -> bool:
        """Simple heuristic to detect potential overflow."""
        text_element = text_match.group(0)

        # Extract x position
        x_match = re.search(r'x="([^"]*)"', text_element)
        if not x_match:
            return False

        try:
            x_pos = float(x_match.group(1))
        except ValueError:
            return False

        # Extract font size
        font_size = self._extract_font_size(text_element)

        # Extract text content
        text_content = self._extract_text_content(text_element)

        # Estimate text width
        estimated_width = len(text_content) * font_size * self.avg_char_width

        # Check if text likely extends beyond safe area
        text_end = x_pos + estimated_width
        safe_boundary = canvas_width - margin

        # Also check if starting too close to left edge
        too_close_to_left = x_pos < margin
        extends_too_far_right = text_end > safe_boundary

        return too_close_to_left or extends_too_far_right

    def _extract_font_size(self, text_element: str) -> float:
        """Extract font size from text element."""
        # Check font-size attribute
        font_size_match = re.search(r'font-size="([^"]*)"', text_element)
        if font_size_match:
            size_str = font_size_match.group(1)
            # Extract numeric part
            size_match = re.search(r'([\d.]+)', size_str)
            if size_match:
                return float(size_match.group(1))

        # Check style attribute for font-size
        style_match = re.search(r'style="([^"]*)"', text_element)
        if style_match:
            style = style_match.group(1)
            font_size_match = re.search(r'font-size:\s*([\d.]+)', style)
            if font_size_match:
                return float(font_size_match.group(1))

        return 16.0  # Default font size

    def _extract_text_content(self, text_element: str) -> str:
        """Extract text content from element."""
        # Remove tags and get content
        content = re.sub(r'<[^>]*>', ' ', text_element)
        return content.strip()

    def _apply_minimal_fix(self, text_match, canvas_width: int, margin: int) -> str:
        """Apply minimal correction to text element."""
        text_element = text_match.group(0)

        # Try repositioning first (less invasive)
        fixed_element = self._try_reposition(text_element, canvas_width, margin)

        # If repositioning isn't enough, try small font reduction
        if self._appears_to_overflow_after_fix(fixed_element, canvas_width, margin):
            fixed_element = self._try_font_reduction(fixed_element)

        return fixed_element

    def _try_reposition(self, text_element: str, canvas_width: int, margin: int) -> str:
        """Try to fix overflow by adjusting position."""
        x_match = re.search(r'x="([^"]*)"', text_element)
        if not x_match:
            return text_element

        try:
            x_pos = float(x_match.group(1))
        except ValueError:
            return text_element

        # If too close to left edge, move right
        if x_pos < margin:
            new_x = margin + 5
            return text_element.replace(f'x="{x_match.group(1)}"', f'x="{new_x}"')

        # If likely extending past right edge, move left slightly
        font_size = self._extract_font_size(text_element)
        text_content = self._extract_text_content(text_element)
        estimated_width = len(text_content) * font_size * self.avg_char_width

        if x_pos + estimated_width > canvas_width - margin:
            # Move left to fit
            new_x = max(margin, canvas_width - margin - estimated_width)
            return text_element.replace(f'x="{x_match.group(1)}"', f'x="{new_x}"')

        return text_element

    def _try_font_reduction(self, text_element: str) -> str:
        """Apply small font size reduction."""
        current_size = self._extract_font_size(text_element)

        # Reduce by 10% (minimal impact on legibility)
        new_size = current_size * 0.9
        new_size = max(new_size, 10)  # Don't go below 10px

        # Update font-size attribute if it exists
        font_size_match = re.search(r'font-size="([^"]*)"', text_element)
        if font_size_match:
            return text_element.replace(
                f'font-size="{font_size_match.group(1)}"',
                f'font-size="{new_size}px"'
            )

        # Update style attribute if it exists
        style_match = re.search(r'style="([^"]*)"', text_element)
        if style_match:
            style = style_match.group(1)
            if 'font-size:' in style:
                new_style = re.sub(r'font-size:\s*[\d.]+[^;]*', f'font-size:{new_size}px', style)
                return text_element.replace(f'style="{style}"', f'style="{new_style}"')
            else:
                # Add font-size to existing style
                new_style = style.rstrip(';') + f';font-size:{new_size}px'
                return text_element.replace(f'style="{style}"', f'style="{new_style}"')

        # Add font-size attribute if no existing size found
        return text_element.replace('<text', f'<text font-size="{new_size}px"')

    def _appears_to_overflow_after_fix(self, text_element: str, canvas_width: int, margin: int) -> bool:
        """Quick check if element still appears to overflow after initial fix."""
        # Create a fake match object for the updated element
        class FakeMatch:
            def __init__(self, content):
                self.content = content
            def group(self, n):
                return self.content

        fake_match = FakeMatch(text_element)
        return self._appears_to_overflow(fake_match, canvas_width, margin)
