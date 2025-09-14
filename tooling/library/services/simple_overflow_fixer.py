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

        # Get text width (preferring textLength if available)
        text_width = self._get_text_width(text_element)

        # Get text anchor to determine how x position relates to text bounds
        text_anchor = self._extract_text_anchor(text_element)

        # Calculate actual left and right edges based on text-anchor
        left_edge, right_edge = self._calculate_text_bounds(x_pos, text_width, text_anchor)

        # Check if text overflows beyond safe boundaries
        safe_left = margin
        safe_right = canvas_width - margin

        overflows_left = left_edge < safe_left
        overflows_right = right_edge > safe_right

        return overflows_left or overflows_right

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

    def _get_text_width(self, text_element: str) -> float:
        """Get text width, preferring textLength if available, otherwise estimate."""
        # Check for textLength attribute (most accurate)
        textlength_match = re.search(r'textLength="([^"]*)"', text_element)
        if textlength_match:
            try:
                return float(textlength_match.group(1))
            except ValueError:
                pass

        # Fallback to estimation
        font_size = self._extract_font_size(text_element)
        text_content = self._extract_text_content(text_element)
        return len(text_content) * font_size * self.avg_char_width

    def _extract_text_anchor(self, text_element: str) -> str:
        """Extract text-anchor value, defaulting to 'start'."""
        anchor_match = re.search(r'text-anchor="([^"]*)"', text_element)
        if anchor_match:
            return anchor_match.group(1)

        # Check in style attribute
        style_match = re.search(r'style="([^"]*)"', text_element)
        if style_match:
            style = style_match.group(1)
            anchor_style_match = re.search(r'text-anchor:\s*([^;]+)', style)
            if anchor_style_match:
                return anchor_style_match.group(1).strip()

        return 'start'  # Default SVG text-anchor value

    def _calculate_text_bounds(self, x_pos: float, text_width: float, text_anchor: str) -> tuple[float, float]:
        """Calculate left and right edges based on x position, width, and anchor."""
        if text_anchor == 'middle':
            # x is center of text
            half_width = text_width / 2
            left_edge = x_pos - half_width
            right_edge = x_pos + half_width
        elif text_anchor == 'end':
            # x is right edge of text
            left_edge = x_pos - text_width
            right_edge = x_pos
        else:  # 'start' or any other value
            # x is left edge of text
            left_edge = x_pos
            right_edge = x_pos + text_width

        return left_edge, right_edge

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

        # Get text properties for correct calculation
        text_width = self._get_text_width(text_element)
        text_anchor = self._extract_text_anchor(text_element)

        # Calculate current bounds
        left_edge, right_edge = self._calculate_text_bounds(x_pos, text_width, text_anchor)

        # Define safe boundaries
        safe_left = margin
        safe_right = canvas_width - margin

        # Calculate new x position to fit within safe boundaries
        new_x = x_pos  # Start with current position

        if left_edge < safe_left:
            # Text overflows left, need to move right
            if text_anchor == 'middle':
                # For middle anchor, x should be: safe_left + (text_width/2)
                new_x = safe_left + (text_width / 2)
            elif text_anchor == 'end':
                # For end anchor, x should be: safe_left + text_width
                new_x = safe_left + text_width
            else:  # 'start'
                # For start anchor, x should be: safe_left
                new_x = safe_left

        elif right_edge > safe_right:
            # Text overflows right, need to move left
            if text_anchor == 'middle':
                # For middle anchor, x should be: safe_right - (text_width/2)
                new_x = safe_right - (text_width / 2)
            elif text_anchor == 'end':
                # For end anchor, x should be: safe_right
                new_x = safe_right
            else:  # 'start'
                # For start anchor, x should be: safe_right - text_width
                new_x = safe_right - text_width

        # Apply the new position if it changed
        if abs(new_x - x_pos) > 0.1:  # Only update if significant change
            return text_element.replace(f'x="{x_match.group(1)}"', f'x="{new_x:.1f}"')

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
