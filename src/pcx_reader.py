"""
PCX file format reader and decoder
Handles PCX header parsing, RLE decompression, and color palette extraction
"""
import struct
from PIL import Image


class PCXHeader:
    """PCX file header structure (128 bytes)."""
    
    def __init__(self, data):
        """Parse PCX header from raw bytes."""
        if len(data) < 128:
            raise ValueError("Invalid PCX header: insufficient data")
        
        # Parse header fields
        self.manufacturer = data[0]
        self.version = data[1]
        self.encoding = data[2]
        self.bits_per_pixel = data[3]
        
        # Window/Image dimensions (4 16-bit values: Xmin, Ymin, Xmax, Ymax)
        self.xmin = struct.unpack('<H', data[4:6])[0]
        self.ymin = struct.unpack('<H', data[6:8])[0]
        self.xmax = struct.unpack('<H', data[8:10])[0]
        self.ymax = struct.unpack('<H', data[10:12])[0]
        
        # DPI
        self.hdpi = struct.unpack('<H', data[12:14])[0]
        self.vdpi = struct.unpack('<H', data[14:16])[0]
        
        # Header colormap (16 colors, RGB triplets)
        self.header_palette = []
        for i in range(16):
            r = data[16 + i * 3]
            g = data[16 + i * 3 + 1]
            b = data[16 + i * 3 + 2]
            self.header_palette.append((r, g, b))
        
        self.reserved = data[64]
        self.num_planes = data[65]
        self.bytes_per_line = struct.unpack('<H', data[66:68])[0]
        self.palette_info = struct.unpack('<H', data[68:70])[0]
        self.hscreen_size = struct.unpack('<H', data[70:72])[0]
        self.vscreen_size = struct.unpack('<H', data[72:74])[0]
        
        # Calculate image dimensions
        self.width = self.xmax - self.xmin + 1
        self.height = self.ymax - self.ymin + 1
    
    def is_valid(self):
        """Check if this is a valid PCX file."""
        return self.manufacturer == 10
    
    def get_version_string(self):
        """Get human-readable version string."""
        versions = {
            0: "Ver. 2.5 of PC Paintbrush",
            2: "Ver. 2.8 w/palette information",
            3: "Ver. 2.8 w/o palette information",
            4: "PC Paintbrush for Windows",
            5: "Ver. 3.0+ of PC Paintbrush"
        }
        return versions.get(self.version, f"Unknown ({self.version})")
    
    def get_palette_info_string(self):
        """Get human-readable palette info string."""
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
    """PCX file reader and decoder."""
    
    def __init__(self, filepath):
        """Load and parse PCX file."""
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.data = f.read()
        
        # Parse header
        self.header = PCXHeader(self.data[:128])
        
        if not self.header.is_valid():
            raise ValueError("Not a valid PCX file")
        
        # Extract color palette if available
        self.palette = self._extract_palette()
        
        # Decode image data
        self.image = self._decode_image()
    
    def _extract_palette(self):
        """Extract 256-color palette from end of file if present."""
        # Check if file has 256-color palette (version 5)
        if self.header.version >= 5 and len(self.data) > 768:
            # Check for palette marker (byte value 12) at position -769
            if len(self.data) >= 769 and self.data[-769] == 12:
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
    
    def _decode_rle_scanline(self, data, start_pos, bytes_per_line):
        """Decode one RLE-compressed scanline."""
        decoded = []
        pos = start_pos
        
        while len(decoded) < bytes_per_line and pos < len(data):
            byte = data[pos]
            pos += 1
            
            # Check if two high bits are set (RLE marker)
            if (byte & 0xC0) == 0xC0:
                # This is a run count
                count = byte & 0x3F  # Remove the two high bits
                if pos < len(data):
                    value = data[pos]
                    pos += 1
                    decoded.extend([value] * count)
            else:
                # Raw byte value
                decoded.append(byte)
        
        return decoded, pos
    
    def _decode_image(self):
        """Decode PCX image data using RLE decompression."""
        width = self.header.width
        height = self.header.height
        bits_per_pixel = self.header.bits_per_pixel
        num_planes = self.header.num_planes
        bytes_per_line = self.header.bytes_per_line
        
        # Start reading image data after 128-byte header
        pos = 128
        
        # Determine where image data ends (before palette if present)
        if self.palette and len(self.data) >= 769:
            end_pos = len(self.data) - 769
        else:
            end_pos = len(self.data)
        
        # Decode all scanlines
        scanlines = []
        for _ in range(height):
            plane_data = []
            for _ in range(num_planes):
                if pos >= end_pos:
                    break
                line, pos = self._decode_rle_scanline(self.data, pos, bytes_per_line)
                plane_data.append(line[:width])  # Trim to actual width
            scanlines.append(plane_data)
        
        # Convert to PIL Image based on color depth
        if num_planes == 3 and bits_per_pixel == 8:
            # 24-bit RGB
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
        
        elif num_planes == 1 and bits_per_pixel == 8:
            # 8-bit: either indexed color (with palette) or grayscale (without palette)
            if self.palette:
                # 8-bit indexed color
                img = Image.new('P', (width, height))
                palette_flat = []
                for r, g, b in self.palette:
                    palette_flat.extend([r, g, b])
                img.putpalette(palette_flat)
                
                # Set pixel data
                pixels = []
                for scanline in scanlines:
                    pixels.extend(scanline[0][:width])
                img.putdata(pixels)
                return img.convert('RGB')
            else:
                # 8-bit grayscale
                img = Image.new('L', (width, height))
                pixels = []
                for scanline in scanlines:
                    pixels.extend(scanline[0][:width])
                img.putdata(pixels)
                return img.convert('RGB')
        
        else:
            # Try to handle other formats using PIL's built-in PCX support
            from io import BytesIO
            try:
                img = Image.open(BytesIO(self.data))
                return img.convert('RGB')
            except Exception:
                # Fallback: create grayscale image
                img = Image.new('L', (width, height))
                pixels = []
                for scanline in scanlines:
                    if scanline:
                        pixels.extend(scanline[0][:width])
                img.putdata(pixels)
                return img.convert('RGB')
    
    def get_palette_image(self, cell_size=16):
        """Create a visual representation of the color palette."""
        if not self.palette:
            return None
        
        # Create a grid of color swatches
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
