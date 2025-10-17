"""PCX reader: parse header, extract palette, decode RLE, build PIL Image.

This module focuses on clarity: small helpers that turn a .pcx file
into a ready-to-use PIL Image and (optionally) a palette preview.
"""

import struct
from PIL import Image


class PCXHeader:
    """PCX file header structure (128 bytes)."""
    
    def __init__(self, data):
        """Parse a 128-byte header buffer into attributes.

        Raises ValueError when the header is too short.
        """
        if len(data) < 128:
            raise ValueError("Invalid PCX header: insufficient data")

        # Basic header fields
        self.manufacturer = data[0]
        self.version = data[1]
        self.encoding = data[2]
        self.bits_per_pixel = data[3]
        
        # Window/Image dimensions (4 16-bit values: Xmin, Ymin, Xmax, Ymax)
        self.xmin = struct.unpack('<H', data[4:6])[0]
        self.ymin = struct.unpack('<H', data[6:8])[0]
        self.xmax = struct.unpack('<H', data[8:10])[0]
        self.ymax = struct.unpack('<H', data[10:12])[0]

        # DPI fields
        self.hdpi = struct.unpack('<H', data[12:14])[0]
        self.vdpi = struct.unpack('<H', data[14:16])[0]

        # header palette (16 * RGB triplets)
        self.header_palette = []
        for i in range(16):
            r = data[16 + i * 3]
            g = data[16 + i * 3 + 1]
            b = data[16 + i * 3 + 2]
            self.header_palette.append((r, g, b))

        # additional metadata used by decoder
        self.reserved = data[64]
        self.num_planes = data[65]
        self.bytes_per_line = struct.unpack('<H', data[66:68])[0]
        self.palette_info = struct.unpack('<H', data[68:70])[0]
        self.hscreen_size = struct.unpack('<H', data[70:72])[0]
        self.vscreen_size = struct.unpack('<H', data[72:74])[0]

        # derived image size
        self.width = self.xmax - self.xmin + 1
        self.height = self.ymax - self.ymin + 1

    def is_valid(self):
        """Check if this is a valid PCX file."""
        return self.manufacturer == 10

    def get_version_string(self):
        versions = {
            0: "Ver. 2.5 of PC Paintbrush",
            2: "Ver. 2.8 w/palette information",
            3: "Ver. 2.8 w/o palette information",
            4: "PC Paintbrush for Windows",
            5: "Ver. 3.0+ of PC Paintbrush"
        }
        return versions.get(self.version, f"Unknown ({self.version})")

    def get_palette_info_string(self):
        if self.palette_info == 1:
            return "Color/BW"
        elif self.palette_info == 2:
            return "Grayscale"
        return str(self.palette_info)

    def __str__(self):
        """String representation of header info."""
        return f"""PCX Header Information:
    Manufacturer: Zsoft .pcx ({self.manufacturer})
    Version: {self.version}
    Encoding: {self.encoding}
    Bits per Pixel: {self.bits_per_pixel}
    Image Dimensions: {self.xmin} {self.ymin} {self.xmax} {self.ymax}
    HDPI: {self.hdpi}
    VDPI: {self.vdpi}
    Number of Color Planes: {self.num_planes}
    Bytes per Line: {self.bytes_per_line}
    Palette Information: {self.palette_info}
    Horizontal Screen Size: {self.hscreen_size}
    Vertical Screen Size: {self.vscreen_size}"""


class PCXReader:
    """Load and decode a PCX file into a PIL Image.

    Steps:
      - read raw file bytes
      - parse header
      - extract 256-color palette if present
      - decode RLE-compressed image data
      - construct a PIL Image with RGB data
    """

    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.data = f.read()

        # Parse header and validate
        self.header = PCXHeader(self.data[:128])
        if not self.header.is_valid():
            raise ValueError("Not a valid PCX file")

        # Palette (None when not available)
        self.palette = self._extract_palette()

        # Decoded PIL Image
        self.image = self._decode_image()

    def _extract_palette(self):
        """Extract 256-color palette from end of file if present."""
        # First, try to locate the palette immediately following the RLE image data
        # per PCX spec: a single 0x0C byte then 768 bytes of RGB triplets
        if self.header.version >= 5:
            rle_end = self._find_rle_end()
            if rle_end is not None and rle_end + 769 <= len(self.data):
                if self.data[rle_end] == 12:
                    palette_data = self.data[rle_end + 1:rle_end + 1 + 768]
                    palette = []
                    for i in range(256):
                        r = palette_data[i * 3]
                        g = palette_data[i * 3 + 1]
                        b = palette_data[i * 3 + 2]
                        palette.append((r, g, b))
                    return palette
                # Try without marker - palette might be directly after RLE
                elif rle_end + 768 <= len(self.data):
                    palette_data = self.data[rle_end:rle_end + 768]
                    palette = []
                    for i in range(256):
                        r = palette_data[i * 3]
                        g = palette_data[i * 3 + 1]
                        b = palette_data[i * 3 + 2]
                        palette.append((r, g, b))
                    return palette

        # Fallback: some encoders write the palette at EOF-769..EOF
        if self.header.version >= 5 and len(self.data) > 768:
            if len(self.data) >= 769 and self.data[-769] == 12:
                palette_data = self.data[-768:]
                palette = []
                for i in range(256):
                    r = palette_data[i * 3]
                    g = palette_data[i * 3 + 1]
                    b = palette_data[i * 3 + 2]
                    palette.append((r, g, b))
                return palette
            # Try last 768 bytes without marker
            elif len(self.data) >= 768:
                palette_data = self.data[-768:]
                palette = []
                for i in range(256):
                    r = palette_data[i * 3]
                    g = palette_data[i * 3 + 1]
                    b = palette_data[i * 3 + 2]
                    palette.append((r, g, b))
                return palette

        # Use header palette for 16-color images
        if self.header.bits_per_pixel <= 4:
            return self.header.header_palette
        
        return None

    def _find_rle_end(self):
        """Decode RLE just enough to compute the byte position where image data ends."""
        data = self.data
        height = self.header.height
        num_planes = self.header.num_planes
        bytes_per_line = self.header.bytes_per_line

        pos = 128
        try:
            for _ in range(height):
                for _ in range(num_planes):
                    decoded = 0
                    while decoded < bytes_per_line and pos < len(data):
                        byte = data[pos]
                        pos += 1
                        if (byte & 0xC0) == 0xC0:
                            # RLE run: next byte is the value, count is in low 6 bits
                            count = byte & 0x3F
                            if pos < len(data):
                                pos += 1  # skip the value byte
                            decoded += count
                        else:
                            # Literal byte
                            decoded += 1
            return pos
        except Exception:
            return None

    def _decode_rle_scanline(self, data, start_pos, bytes_per_line):
        """Decode a single RLE scanline. Return (decoded_list, new_pos)."""
        decoded = []
        pos = start_pos

        while len(decoded) < bytes_per_line and pos < len(data):
            byte = data[pos]
            pos += 1
            # 0xC0 prefix indicates a run: top two bits set
            if (byte & 0xC0) == 0xC0:
                count = byte & 0x3F
                if pos < len(data):
                    value = data[pos]
                    pos += 1
                    decoded.extend([value] * count)
            else:
                # raw value
                decoded.append(byte)

        return decoded, pos

    def _decode_image(self):
        """Decode entire image data using header metadata and RLE decoder."""
        width = self.header.width
        height = self.header.height
        bits_per_pixel = self.header.bits_per_pixel
        num_planes = self.header.num_planes
        bytes_per_line = self.header.bytes_per_line

        pos = 128  # image data starts after header

        # if a 256-color palette exists, image data ends before that block
        if self.palette and len(self.data) >= 769:
            end_pos = len(self.data) - 769
        else:
            end_pos = len(self.data)

        # Decode each scanline for every plane
        scanlines = []
        for _ in range(height):
            plane_data = []
            for _ in range(num_planes):
                if pos >= end_pos:
                    break
                line, pos = self._decode_rle_scanline(self.data, pos, bytes_per_line)
                plane_data.append(line[:width])  # trim to width
            scanlines.append(plane_data)

        # Assemble decoded data into a PIL Image depending on format
        if num_planes == 3 and bits_per_pixel == 8:
            # 24-bit RGB (three planes)
            img = Image.new('RGB', (width, height))
            pixels = []
            for scanline in scanlines:
                for x in range(width):
                    if x < len(scanline[0]):
                        r = scanline[0][x]
                        g = scanline[1][x]
                        b = scanline[2][x]
                        pixels.append((r, g, b))
            img.putdata(pixels)
            return img

        # 8-bit single-plane: either indexed (with palette) or grayscale
        elif num_planes == 1 and bits_per_pixel == 8:
            if self.palette:
                # Convert indexed pixels using palette luminance so display remains grayscale
                # even when a colored VGA palette is present after image data.
                grayscale_map = []
                for r, g, b in self.palette:
                    # ITU-R BT.601 luma approximation with rounding
                    y = int(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
                    if y < 0:
                        y = 0
                    elif y > 255:
                        y = 255
                    grayscale_map.append(y)

                img = Image.new('L', (width, height))
                pixels = []
                for scanline in scanlines:
                    indices = scanline[0][:width]
                    # Map palette indices to grayscale luminance
                    pixels.extend([grayscale_map[idx] if idx < len(grayscale_map) else idx for idx in indices])
                img.putdata(pixels)
                return img.convert('RGB')
            else:
                img = Image.new('L', (width, height))
                pixels = []
                for scanline in scanlines:
                    pixels.extend(scanline[0][:width])
                img.putdata(pixels)
                return img.convert('RGB')

        else:
            # Last resort: let PIL attempt to open the file bytes directly
            from io import BytesIO
            try:
                img = Image.open(BytesIO(self.data))
                return img.convert('RGB')
            except Exception:
                # Fallback to grayscale assembly
                img = Image.new('L', (width, height))
                pixels = []
                for scanline in scanlines:
                    if scanline:
                        pixels.extend(scanline[0][:width])
                img.putdata(pixels)
                return img.convert('RGB')

    def get_palette_image(self, cell_size=16):
        """Create a visual representation of the file palette ordered by index.

        This is useful for images that carry an explicit 256-color VGA palette.
        For grayscale or images without a palette, prefer
        get_palette_preview_from_image.
        """
        if not self.palette:
            return None

        # When rendering a palette for 8-bit single-plane images, display
        # grayscale luminance of the palette (since pixels are used as L).
        palette_colors = self.palette
        if self.header.bits_per_pixel == 8 and self.header.num_planes == 1:
            converted = []
            for r, g, b in palette_colors:
                y = int(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
                if y < 0:
                    y = 0
                elif y > 255:
                    y = 255
                converted.append((y, y, y))
            palette_colors = converted

        colors_per_row = 16
        num_colors = len(palette_colors)
        num_rows = (num_colors + colors_per_row - 1) // colors_per_row

        img_width = colors_per_row * cell_size
        img_height = num_rows * cell_size

        img = Image.new('RGB', (img_width, img_height))
        pixels = []

        for row in range(num_rows):
            for _ in range(cell_size):
                for col in range(colors_per_row):
                    color_idx = row * colors_per_row + col
                    if color_idx < num_colors:
                        color = palette_colors[color_idx]
                    else:
                        color = (0, 0, 0)
                    pixels.extend([color] * cell_size)

        img.putdata(pixels)
        return img

    def get_palette_preview_from_image(self, cell_size=16, max_colors=256):
        """Create a palette preview derived from the image's actually used colors.

        - Collects colors (grayscale or RGB) from the decoded image
        - Sorts by frequency (most common first)
        - Renders a 16xN grid up to max_colors entries
        """
        if not self.image:
            return None

        # Work in a compact color space for counting
        if self.image.mode == 'L':
            src = self.image
        else:
            src = self.image.convert('RGB')

        pixels = list(src.getdata())

        # Build histogram of colors
        color_to_count = {}
        if src.mode == 'L':
            for v in pixels:
                color_to_count[v] = color_to_count.get(v, 0) + 1
            # Convert keys to RGB triples for visualization
            colors = [((v, v, v), c) for v, c in color_to_count.items()]
        else:
            for rgb in pixels:
                color_to_count[rgb] = color_to_count.get(rgb, 0) + 1
            colors = [(rgb, c) for rgb, c in color_to_count.items()]

        # Sort by frequency desc, then by value for determinism
        colors.sort(key=lambda x: (-x[1], x[0]))
        ordered_colors = [rgb for rgb, _ in colors[:max_colors]]

        colors_per_row = 16
        num_colors = len(ordered_colors)
        if num_colors == 0:
            return None
        num_rows = (num_colors + colors_per_row - 1) // colors_per_row

        img_width = colors_per_row * cell_size
        img_height = num_rows * cell_size
        img = Image.new('RGB', (img_width, img_height))

        pixels_out = []
        for row in range(num_rows):
            for _ in range(cell_size):
                for col in range(colors_per_row):
                    color_idx = row * colors_per_row + col
                    if color_idx < num_colors:
                        color = ordered_colors[color_idx]
                    else:
                        color = (0, 0, 0)
                    pixels_out.extend([color] * cell_size)

        img.putdata(pixels_out)
        return img

    def get_palette_image_raw(self, cell_size=16):
        """Create a raw RGB palette grid (no grayscale conversion).

        This is useful for comparing the file's actual palette colors
        against the grayscale interpretation used for display.
        """
        if not self.palette:
            return None

        colors_per_row = 16
        num_colors = len(self.palette)
        num_rows = (num_colors + colors_per_row - 1) // colors_per_row

        img_width = colors_per_row * cell_size
        img_height = num_rows * cell_size

        img = Image.new('RGB', (img_width, img_height))
        pixels = []

        for row in range(num_rows):
            for _ in range(cell_size):
                for col in range(colors_per_row):
                    color_idx = row * colors_per_row + col
                    if color_idx < num_colors:
                        color = self.palette[color_idx]
                    else:
                        color = (0, 0, 0)
                    pixels.extend([color] * cell_size)

        img.putdata(pixels)
        return img