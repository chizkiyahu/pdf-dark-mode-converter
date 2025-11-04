"""
PDF Vector Processor - Dark Mode Conversion Engine

This module provides vector-based PDF dark mode conversion using pikepdf for content
stream manipulation. Unlike raster-based approaches, this preserves text quality,
searchability, and all PDF features while transforming colors to dark mode.

Key Features:
    - Vector-based processing: Preserves text quality and searchability
    - Content stream manipulation: Directly modifies PDF color operators
    - Multi-theme support: Six predefined dark mode color themes
    - HSV color space transformations: Preserves hue while adjusting brightness
    - CMYK support: Handles all major PDF color spaces (RGB, CMYK, Grayscale)
    - Smart color transformation: Different strategies for backgrounds, text, and colored elements

Technical Approach:
    The processor works by:
    1. Adding a dark background layer underneath existing content
    2. Using regex to find color operators in PDF content streams
    3. Transforming colors based on brightness and saturation
    4. Preserving hue for colored elements while brightening them for visibility

Color Transformation Strategy:
    - White/light backgrounds (>93% brightness) → Theme background color
    - Black/dark text (<15% brightness, low saturation) → Bright white
    - Dark colored elements (<15% brightness, high saturation) → Brightened colored values
    - Medium tones → Adjusted brightness while preserving hue

Supported Color Spaces:
    - RGB (rg/RG operators)
    - Grayscale (g/G operators)
    - CMYK (k/K operators)

Dependencies:
    - pikepdf: PDF manipulation library
    - reportlab: Background layer generation
    - re: Pattern matching for color operators
    - typing: Type hints

Usage:
    processor = PDFVectorProcessorPikePDF(theme="classic")
    with open("input.pdf", "rb") as f:
        input_bytes = f.read()
    output_bytes = processor.process_pdf(input_bytes)
    with open("output.pdf", "wb") as f:
        f.write(output_bytes)

Author: PDF Dark Mode Converter Project
License: MIT
"""

import pikepdf
from pikepdf import Pdf, Name, Array, Operator, Rectangle
import io
import re
from typing import Tuple, List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class PDFVectorProcessorPikePDF:
    """
    Vector-based PDF dark mode processor using content stream manipulation.

    This class transforms PDF documents to dark mode while preserving text quality
    and searchability. It operates by adding dark backgrounds and transforming
    color operators in PDF content streams.

    The processor uses intelligent color transformation based on:
    - Brightness levels (separating text, backgrounds, and content)
    - Color saturation (distinguishing grayscale from colored elements)
    - HSV color space (preserving hue while adjusting brightness)

    Attributes:
        theme (str): Selected theme name (e.g., "classic", "claude", "chatgpt")
        themes (dict): Dictionary of available themes with RGB values (0-255)
        bg_color (dict): Current theme's background color {"r": int, "g": int, "b": int}
        pdf (Pdf): The pikepdf.Pdf object being processed

    Available Themes:
        - classic: Pure black (0, 0, 0) - Traditional dark mode
        - claude: Warm brown (42, 37, 34) - Inspired by Claude AI interface
        - chatgpt: Dark blue-gray (52, 53, 65) - Inspired by ChatGPT interface
        - sepia: Dark brown (40, 35, 25) - Warm sepia tone
        - midnight: Dark blue (25, 30, 45) - Cool midnight blue
        - forest: Dark green (25, 35, 30) - Natural forest green

    Color Operator Coverage:
        RGB:
            - rg: Non-stroking (fill) RGB color
            - RG: Stroking (outline) RGB color
        Grayscale:
            - g: Non-stroking grayscale
            - G: Stroking grayscale
        CMYK:
            - k: Non-stroking CMYK color
            - K: Stroking CMYK color
    """

    def __init__(self, theme: str = "classic"):
        """
        Initialize the PDF vector processor with a specific theme.

        Args:
            theme (str, optional): Theme name for dark mode. Must be one of:
                "classic", "claude", "chatgpt", "sepia", "midnight", "forest".
                Defaults to "classic" (pure black background).

        Raises:
            KeyError: If an invalid theme name is provided (falls back to "classic")
        """
        self.theme = theme
        self.themes = {
            "classic": {"r": 0, "g": 0, "b": 0},
            "claude": {"r": 42, "g": 37, "b": 34},
            "chatgpt": {"r": 52, "g": 53, "b": 65},
            "sepia": {"r": 40, "g": 35, "b": 25},
            "midnight": {"r": 25, "g": 30, "b": 45},
            "forest": {"r": 25, "g": 35, "b": 30}
        }
        self.bg_color = self.themes.get(theme, self.themes["classic"])

    def process_pdf(self, input_bytes: bytes) -> bytes:
        """
        Process a PDF and convert it to dark mode.

        Main entry point for PDF conversion. Opens the PDF from bytes, processes
        each page by adding dark backgrounds and transforming colors, then returns
        the modified PDF as bytes.

        Processing steps:
        1. Opens PDF from input bytes using pikepdf
        2. Iterates through all pages
        3. For each page:
           - Creates a dark background matching page dimensions
           - Adds background as underlay (beneath existing content)
           - Transforms color operators in content streams
        4. Saves modified PDF to bytes and returns

        Args:
            input_bytes (bytes): Raw bytes of the input PDF file

        Returns:
            bytes: Raw bytes of the processed PDF with dark mode applied

        Raises:
            pikepdf.PdfError: If the input bytes are not a valid PDF
            Exception: Any errors during processing are caught and logged per-page,
                      allowing the rest of the document to process

        Example:
            >>> processor = PDFVectorProcessorPikePDF(theme="classic")
            >>> with open("input.pdf", "rb") as f:
            ...     pdf_bytes = f.read()
            >>> output_bytes = processor.process_pdf(pdf_bytes)
            >>> with open("output.pdf", "wb") as f:
            ...     f.write(output_bytes)
        """
        # Open PDF
        self.pdf = Pdf.open(io.BytesIO(input_bytes))

        # Process each page (create background per page for correct dimensions)
        for page in self.pdf.pages:
            self._process_page(page)

        # Save to bytes
        output = io.BytesIO()
        self.pdf.save(output)
        output.seek(0)

        result = output.getvalue()
        self.pdf.close()

        return result

    def _create_background_pdf(self, width, height) -> Pdf:
        """
        Create a single-page PDF containing only a dark background rectangle.

        Uses reportlab to generate a temporary PDF with a filled rectangle matching
        the specified dimensions and the current theme's background color. This PDF
        is then opened with pikepdf and used as an underlay for the original pages.

        Args:
            width (float): Width of the background rectangle in PDF units (points)
            height (float): Height of the background rectangle in PDF units (points)

        Returns:
            Pdf: A pikepdf.Pdf object containing a single page with a solid dark background

        Note:
            The background color is determined by self.bg_color which is set based on
            the selected theme. Colors are normalized from 0-255 range to 0-1 range
            for reportlab compatibility.
        """
        packet = io.BytesIO()
        # Use the exact page dimensions
        can = canvas.Canvas(packet, pagesize=(width, height))

        # Set fill color to theme color
        bg_r = self.bg_color["r"] / 255.0
        bg_g = self.bg_color["g"] / 255.0
        bg_b = self.bg_color["b"] / 255.0

        can.setFillColorRGB(bg_r, bg_g, bg_b)
        can.rect(0, 0, width, height, fill=True, stroke=False)
        can.save()

        packet.seek(0)
        return Pdf.open(packet)

    def _process_page(self, page):
        """
        Process a single PDF page by adding background and transforming colors.

        This method performs the core page-level transformation:
        1. Extracts page dimensions from MediaBox
        2. Creates a dark background PDF matching those dimensions
        3. Adds the background as an underlay (beneath all existing content)
        4. Reads the page's content stream(s)
        5. Transforms color operators in the content stream
        6. Replaces the content stream with the modified version

        Content Stream Handling:
            - Handles both single content streams and arrays of content streams
            - Combines multiple streams into a single transformed stream
            - Decodes content using latin-1 encoding with error tolerance
            - Encodes modified content back to latin-1 for PDF compatibility

        Args:
            page (pikepdf.Page): The PDF page object to process

        Raises:
            Exception: Catches and logs any errors during page processing without
                      propagating them, allowing other pages to be processed

        Note:
            If a page has no Contents key (blank page), it is skipped after adding
            the background. Debug output is printed for white/light colors and
            dark colored values being transformed.
        """
        try:
            # Get page dimensions
            mediabox = page.MediaBox
            width = float(mediabox[2] - mediabox[0])
            height = float(mediabox[3] - mediabox[1])

            # Create a background PDF with the exact page dimensions
            bg_pdf = self._create_background_pdf(width, height)
            bg_page = bg_pdf.pages[0]

            # Add dark background as underlay (below all content)
            bg_rect = Rectangle(0, 0, width, height)
            page.add_underlay(bg_page, bg_rect)

            # Close the background PDF
            bg_pdf.close()

            # Now transform the colors in the existing content
            if Name.Contents not in page:
                return

            contents = page.Contents

            # Collect all content and transform it
            all_content = []

            # Handle array of content streams
            if isinstance(contents, pikepdf.Array):
                for i, stream in enumerate(contents):
                    if hasattr(stream, 'read_bytes'):
                        content_data = stream.read_bytes()
                        content_str = content_data.decode('latin-1', errors='ignore')
                        all_content.append(content_str)

            # Handle single content stream
            elif hasattr(contents, 'read_bytes'):
                content_data = contents.read_bytes()
                content_str = content_data.decode('latin-1', errors='ignore')
                all_content.append(content_str)

            # Combine all content
            combined_content = '\n'.join(all_content)

            # Transform the combined content (change text/graphic colors)
            modified_content = self._transform_content_stream(combined_content)

            # Create new stream and replace
            new_stream = pikepdf.Stream(self.pdf, modified_content.encode('latin-1'))
            page.Contents = new_stream

        except Exception as e:
            print(f"Warning: Could not process page: {e}")
            import traceback
            traceback.print_exc()

    def _transform_content_stream(self, content: str) -> str:
        """
        Transform all color operators in a PDF content stream using regex.

        This method is the core of the color transformation logic. It uses regular
        expressions to find and replace PDF color operators while preserving all
        other content (text, positioning, graphics commands, etc.).

        The method processes six types of color operators:
        - rg: RGB non-stroking color (fills, text color)
        - RG: RGB stroking color (outlines, borders)
        - g: Grayscale non-stroking color
        - G: Grayscale stroking color
        - k: CMYK non-stroking color
        - K: CMYK stroking color

        For each operator type, it:
        1. Finds all occurrences using regex patterns
        2. Extracts the color values
        3. Passes them to the appropriate transformation method
        4. Replaces the original operator with the transformed values

        Args:
            content (str): The raw content stream as a string (decoded from PDF)

        Returns:
            str: Modified content stream with transformed color operators

        Regex Patterns:
            - Numbers match: integers, decimals, and decimals without leading zero
            - Operators use word boundaries (\\b) to avoid partial matches
            - Whitespace is flexible to handle various PDF formatting styles

        Note:
            The transformations are applied using lambda functions that call
            the appropriate _replace_* method for each color space.
        """
        # Use regex to find and replace color operators

        # RGB non-stroking (rg) - text and fill colors
        # Match numbers like: 0, 0.5, .5, 1.0
        content = re.sub(
            r'(\d*\.?\d+)\s+(\d*\.?\d+)\s+(\d*\.?\d+)\s+rg',
            lambda m: self._replace_rgb(m, 'rg'),
            content
        )

        # RGB stroking (RG) - line colors
        content = re.sub(
            r'(\d*\.?\d+)\s+(\d*\.?\d+)\s+(\d*\.?\d+)\s+RG',
            lambda m: self._replace_rgb(m, 'RG'),
            content
        )

        # Grayscale non-stroking (g) - be more careful with the pattern
        content = re.sub(
            r'(\d+\.?\d*)\s+g\b',
            lambda m: self._replace_gray(m, 'g'),
            content
        )

        # Grayscale stroking (G)
        content = re.sub(
            r'(\d+\.?\d*)\s+G\b',
            lambda m: self._replace_gray(m, 'G'),
            content
        )

        # CMYK non-stroking (k)
        content = re.sub(
            r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+k\b',
            lambda m: self._replace_cmyk(m, 'k'),
            content
        )

        # CMYK stroking (K)
        content = re.sub(
            r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+K\b',
            lambda m: self._replace_cmyk(m, 'K'),
            content
        )

        return content

    def _replace_rgb(self, match, operator):
        """
        Replace a matched RGB color operator with transformed values.

        Callback function for regex substitution. Extracts RGB values from the
        regex match, transforms them using _transform_rgb(), and returns the
        formatted replacement string.

        Debug logging is performed for:
        - White/light colors (brightness > 0.9)
        - Dark colored values (brightness < 0.2 with color saturation)

        Args:
            match (re.Match): Regex match object containing three capture groups for R, G, B
            operator (str): The PDF operator ("rg" or "RG")

        Returns:
            str: Formatted PDF color operator string with transformed values
                 Format: "{new_r:.4f} {new_g:.4f} {new_b:.4f} {operator}"

        Example:
            Input match: "1.0 1.0 1.0 rg" (white)
            Output: "0.0000 0.0000 0.0000 rg" (black for classic theme)
        """
        r = float(match.group(1))
        g = float(match.group(2))
        b = float(match.group(3))

        new_r, new_g, new_b = self._transform_rgb(r, g, b)

        # Debug output
        brightness = 0.299 * r + 0.587 * g + 0.114 * b
        if brightness > 0.9:  # Log white colors
            print(f"Transforming white/light RGB: ({r:.2f}, {g:.2f}, {b:.2f}) -> ({new_r:.2f}, {new_g:.2f}, {new_b:.2f})")
        elif brightness < 0.2 and (g > 0.01 or b > 0.01):  # Log dark colored values
            print(f"Transforming dark colored RGB: ({r:.2f}, {g:.2f}, {b:.2f}) -> ({new_r:.2f}, {new_g:.2f}, {new_b:.2f})")

        return f"{new_r:.4f} {new_g:.4f} {new_b:.4f} {operator}"

    def _replace_gray(self, match, operator):
        """
        Replace a matched grayscale color operator with transformed value.

        Callback function for regex substitution. Extracts the grayscale value
        from the regex match, transforms it using _transform_grayscale(), and
        returns the formatted replacement string.

        Args:
            match (re.Match): Regex match object containing one capture group for gray value
            operator (str): The PDF operator ("g" or "G")

        Returns:
            str: Formatted PDF grayscale operator string with transformed value
                 Format: "{new_gray:.4f} {operator} "
                 Note the trailing space for PDF formatting compatibility

        Example:
            Input match: "0 g" (black)
            Output: "0.9800 g " (bright white)
        """
        gray = float(match.group(1))

        new_gray = self._transform_grayscale(gray)

        return f"{new_gray:.4f} {operator} "

    def _replace_cmyk(self, match, operator):
        """
        Replace a matched CMYK color operator with transformed values.

        Callback function for regex substitution. Extracts CMYK values from the
        regex match, transforms them using _transform_cmyk(), and returns the
        formatted replacement string.

        Args:
            match (re.Match): Regex match object containing four capture groups for C, M, Y, K
            operator (str): The PDF operator ("k" or "K")

        Returns:
            str: Formatted PDF CMYK operator string with transformed values
                 Format: "{new_c:.4f} {new_m:.4f} {new_y:.4f} {new_k:.4f} {operator} "
                 Note the trailing space for PDF formatting compatibility

        Note:
            CMYK values are first converted to RGB, transformed in RGB space,
            then converted back to CMYK. This ensures consistent color behavior
            across different color spaces.

        Example:
            Input match: "0 0 0 1 k" (black in CMYK)
            Output: "0.0000 0.0000 0.0000 0.0200 k " (bright white in CMYK)
        """
        c = float(match.group(1))
        m = float(match.group(2))
        y = float(match.group(3))
        k = float(match.group(4))

        new_c, new_m, new_y, new_k = self._transform_cmyk(c, m, y, k)

        return f"{new_c:.4f} {new_m:.4f} {new_y:.4f} {new_k:.4f} {operator} "

    def _transform_rgb(self, r: float, g: float, b: float) -> Tuple[float, float, float]:
        """
        Transform RGB colors intelligently based on brightness and saturation.

        This is the core color transformation logic that determines how each color
        is converted to dark mode. It uses a multi-tier strategy based on:
        1. Perceived brightness (weighted RGB formula)
        2. Color saturation (to distinguish grayscale from colored elements)
        3. HSV color space manipulation (to preserve hue while adjusting brightness)

        Transformation Strategy:
            Brightness > 0.93 (White/Light Backgrounds):
                → Convert to theme background color (e.g., black for classic)

            Brightness < 0.15, Saturation < 0.3 (Black/Dark Grayscale Text):
                → Convert to bright white (0.98, 0.98, 0.98)

            Brightness < 0.15, Saturation >= 0.3 (Dark Colored Elements):
                → Brighten significantly (V: 0.65-0.85) while preserving hue
                → Boost saturation slightly to maintain color vibrancy

            0.15 <= Brightness < 0.4 (Dark Colors):
                → Brighten to 0.75+ value range
                → Slightly reduce saturation for better readability

            0.4 <= Brightness < 0.6 (Medium-Dark Colors):
                → Brighten to 0.65+ value range
                → Moderate saturation adjustment

            Brightness >= 0.6 (Medium-Light Colors):
                → Moderate brightening (0.5 + original * 0.5)

        Args:
            r (float): Red component (0.0 to 1.0)
            g (float): Green component (0.0 to 1.0)
            b (float): Blue component (0.0 to 1.0)

        Returns:
            Tuple[float, float, float]: Transformed (r, g, b) values, each 0.0-1.0

        Note:
            Uses HSV color space for transformations to preserve hue while adjusting
            brightness. The perceived brightness formula (0.299*R + 0.587*G + 0.114*B)
            weights green more heavily as human eyes are most sensitive to green light.

        Example:
            >>> # White background
            >>> processor._transform_rgb(1.0, 1.0, 1.0)
            (0.0, 0.0, 0.0)  # Black for classic theme

            >>> # Black text
            >>> processor._transform_rgb(0.0, 0.0, 0.0)
            (0.98, 0.98, 0.98)  # Bright white

            >>> # Dark blue element
            >>> processor._transform_rgb(0.0, 0.0, 0.5)
            (0.45, 0.45, 0.85)  # Brightened blue (approximate)
        """
        brightness = 0.299 * r + 0.587 * g + 0.114 * b

        # White/light backgrounds → dark theme color
        if brightness > 0.93:
            return (
                self.bg_color["r"] / 255.0,
                self.bg_color["g"] / 255.0,
                self.bg_color["b"] / 255.0
            )

        # Check if it's a colored dark value (has hue/saturation)
        h, s, v = self._rgb_to_hsv(r, g, b)

        # Very dark with low saturation (grayscale/black text) → bright white
        if brightness < 0.15 and s < 0.3:
            return (0.98, 0.98, 0.98)

        # Very dark with saturation (colored like dark blue) → brighten while keeping hue
        if brightness < 0.15:
            # Map dark colored values (0-0.15) to bright colored values (0.65-0.85)
            v = 0.65 + (v / 0.15) * 0.2  # Scale up significantly
            s = min(s * 1.1, 1.0)  # Slightly boost saturation
            new_r, new_g, new_b = self._hsv_to_rgb(h, s, v)
            # Clamp values to 0-1 range
            return (min(max(new_r, 0), 1), min(max(new_g, 0), 1), min(max(new_b, 0), 1))

        # Dark colors (like dark blue) → brighten significantly
        if brightness < 0.4:
            h, s, v = self._rgb_to_hsv(r, g, b)
            v = 0.75 + (v - 0.15) * 0.8
            s = s * 0.85
            return self._hsv_to_rgb(h, s, v)

        # Medium-dark → brighten moderately
        if brightness < 0.6:
            h, s, v = self._rgb_to_hsv(r, g, b)
            v = 0.65 + (v - 0.4) * 1.0
            s = s * 0.9
            return self._hsv_to_rgb(h, s, v)

        # Other colors
        h, s, v = self._rgb_to_hsv(r, g, b)
        v = 0.5 + v * 0.5
        return self._hsv_to_rgb(h, s, v)

    def _transform_grayscale(self, gray: float) -> float:
        """
        Transform grayscale values for dark mode.

        Applies similar brightness-based transformation as RGB but for single-channel
        grayscale values. This handles PDFs that use the simpler grayscale color space
        instead of RGB.

        Transformation Strategy:
            Gray > 0.93 (White/Light):
                → Convert to theme background color's grayscale equivalent

            Gray < 0.15 (Black/Very Dark):
                → Convert to bright white (0.98)

            0.15 <= Gray < 0.4 (Dark):
                → Brighten to 0.75+ range

            0.4 <= Gray < 0.6 (Medium-Dark):
                → Brighten to 0.65+ range

            Gray >= 0.6 (Medium-Light):
                → Moderate brightening (0.5 + original * 0.5)

        Args:
            gray (float): Grayscale value (0.0 = black to 1.0 = white)

        Returns:
            float: Transformed grayscale value (0.0 to 1.0)

        Note:
            The theme background color is converted to grayscale using the same
            perceptual brightness formula as RGB: 0.299*R + 0.587*G + 0.114*B

        Example:
            >>> # White
            >>> processor._transform_grayscale(1.0)
            0.0  # Theme background

            >>> # Black
            >>> processor._transform_grayscale(0.0)
            0.98  # Bright white
        """
        if gray > 0.93:
            bg_gray = (0.299 * self.bg_color["r"] +
                      0.587 * self.bg_color["g"] +
                      0.114 * self.bg_color["b"]) / 255.0
            return bg_gray

        if gray < 0.15:
            return 0.98

        if gray < 0.4:
            return 0.75 + (gray - 0.15) * 0.8

        if gray < 0.6:
            return 0.65 + (gray - 0.4) * 1.0

        return 0.5 + gray * 0.5

    def _transform_cmyk(self, c: float, m: float, y: float, k: float) -> Tuple[float, float, float, float]:
        """
        Transform CMYK colors by converting to RGB, transforming, and converting back.

        CMYK (Cyan, Magenta, Yellow, Key/Black) is a subtractive color space used
        in printing. To apply consistent color transformations, this method:
        1. Converts CMYK to RGB
        2. Applies RGB dark mode transformation
        3. Converts the result back to CMYK

        This ensures that CMYK colors are transformed consistently with RGB colors
        in the document.

        Conversion Formulas:
            CMYK → RGB:
                R = (1 - C) * (1 - K)
                G = (1 - M) * (1 - K)
                B = (1 - Y) * (1 - K)

            RGB → CMYK:
                K = 1 - max(R, G, B)
                If K < 1:
                    C = (1 - R - K) / (1 - K)
                    M = (1 - G - K) / (1 - K)
                    Y = (1 - B - K) / (1 - K)
                Else:
                    C = M = Y = 0

        Args:
            c (float): Cyan component (0.0 to 1.0)
            m (float): Magenta component (0.0 to 1.0)
            y (float): Yellow component (0.0 to 1.0)
            k (float): Key/Black component (0.0 to 1.0)

        Returns:
            Tuple[float, float, float, float]: Transformed (c, m, y, k) values, each 0.0-1.0

        Example:
            >>> # Pure black in CMYK
            >>> processor._transform_cmyk(0, 0, 0, 1)
            (0.0, 0.0, 0.0, 0.02)  # Bright white in CMYK (approximate)

            >>> # White in CMYK
            >>> processor._transform_cmyk(0, 0, 0, 0)
            (0.0, 0.0, 0.0, 1.0)  # Black in CMYK for classic theme
        """
        # Convert to RGB
        r = (1 - c) * (1 - k)
        g = (1 - m) * (1 - k)
        b = (1 - y) * (1 - k)

        # Transform
        new_r, new_g, new_b = self._transform_rgb(r, g, b)

        # Convert back to CMYK
        if new_r == 0 and new_g == 0 and new_b == 0:
            return 0, 0, 0, 1

        new_k = 1 - max(new_r, new_g, new_b)
        if new_k < 1:
            new_c = (1 - new_r - new_k) / (1 - new_k)
            new_m = (1 - new_g - new_k) / (1 - new_k)
            new_y = (1 - new_b - new_k) / (1 - new_k)
        else:
            new_c = 0
            new_m = 0
            new_y = 0

        return new_c, new_m, new_y, new_k

    def _rgb_to_hsv(self, r: float, g: float, b: float) -> Tuple[float, float, float]:
        """
        Convert RGB color values to HSV (Hue, Saturation, Value) color space.

        HSV is a cylindrical color space that separates chromatic content (hue and
        saturation) from brightness (value). This makes it ideal for color
        transformations that need to preserve hue while adjusting brightness.

        Calculation:
            1. Find max and min of R, G, B components
            2. Hue (H): Based on which component is maximum
               - If R is max: H = 60 * ((G - B) / diff)
               - If G is max: H = 60 * ((B - R) / diff) + 120
               - If B is max: H = 60 * ((R - G) / diff) + 240
               - Normalized to 0-360 degrees, then scaled to 0-1
            3. Saturation (S): diff / max (0 if max is 0)
            4. Value (V): max component value

        Args:
            r (float): Red component (0.0 to 1.0)
            g (float): Green component (0.0 to 1.0)
            b (float): Blue component (0.0 to 1.0)

        Returns:
            Tuple[float, float, float]: (h, s, v) where:
                - h (hue): 0.0-1.0 (0-360 degrees normalized)
                - s (saturation): 0.0-1.0 (0% to 100%)
                - v (value/brightness): 0.0-1.0 (0% to 100%)

        Example:
            >>> processor._rgb_to_hsv(1.0, 0.0, 0.0)  # Pure red
            (0.0, 1.0, 1.0)  # H=0 (red), S=100%, V=100%

            >>> processor._rgb_to_hsv(0.5, 0.5, 0.5)  # Gray
            (0.0, 0.0, 0.5)  # H=0 (undefined), S=0%, V=50%
        """
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val

        if diff == 0:
            h = 0
        elif max_val == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_val == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360

        s = 0 if max_val == 0 else (diff / max_val)
        v = max_val

        return h / 360.0, s, v

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[float, float, float]:
        """
        Convert HSV (Hue, Saturation, Value) color values back to RGB color space.

        This is the inverse operation of _rgb_to_hsv. It's used after manipulating
        colors in HSV space (typically adjusting brightness while preserving hue)
        to convert back to RGB for use in PDF color operators.

        Calculation:
            1. Convert normalized hue (0-1) back to degrees (0-360)
            2. Calculate intermediate values:
               - C (chroma): V * S
               - X: C * (1 - |((H / 60) mod 2) - 1|)
               - m (match): V - C
            3. Determine R', G', B' based on hue sector (60-degree segments)
            4. Add m to each component: R = R' + m, G = G' + m, B = B' + m

        Hue Sectors:
            0-60°: (C, X, 0) + m → Red to Yellow
            60-120°: (X, C, 0) + m → Yellow to Green
            120-180°: (0, C, X) + m → Green to Cyan
            180-240°: (0, X, C) + m → Cyan to Blue
            240-300°: (X, 0, C) + m → Blue to Magenta
            300-360°: (C, 0, X) + m → Magenta to Red

        Args:
            h (float): Hue (0.0 to 1.0, representing 0-360 degrees)
            s (float): Saturation (0.0 to 1.0, 0% to 100%)
            v (float): Value/Brightness (0.0 to 1.0, 0% to 100%)

        Returns:
            Tuple[float, float, float]: (r, g, b) where each component is 0.0-1.0

        Example:
            >>> processor._hsv_to_rgb(0.0, 1.0, 1.0)  # Pure red in HSV
            (1.0, 0.0, 0.0)  # Pure red in RGB

            >>> processor._hsv_to_rgb(0.333, 1.0, 1.0)  # Green in HSV
            (0.0, 1.0, 0.0)  # Green in RGB (approximate)

            >>> processor._hsv_to_rgb(0.0, 0.0, 0.5)  # Gray in HSV
            (0.5, 0.5, 0.5)  # Gray in RGB
        """
        h = h * 360.0
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c

        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        return r + m, g + m, b + m
