"""
Image manipulation tools using PIL
"""
from PIL import Image, ImageOps, ImageEnhance


class ImageTools:
    """Static helper functions performing PIL-based edits returning new PIL Images."""
    
    @staticmethod
    def invert(im):
        # Invert colors and return RGB image
        return ImageOps.invert(im.convert("RGB"))

    @staticmethod
    def to_grayscale(im):
        # Convert to grayscale then back to RGB to keep display code simple
        return ImageOps.grayscale(im).convert("RGB")

    @staticmethod
    def brightness(im, factor):
        # Adjust brightness by factor (1.0 = no change)
        return ImageEnhance.Brightness(im).enhance(factor).convert("RGB")

    @staticmethod
    def contrast(im, factor):
        # Adjust contrast by factor (1.0 = no change)
        return ImageEnhance.Contrast(im).enhance(factor).convert("RGB")

    @staticmethod
    def photo_filter(im, color=(255, 165, 0), density=0.2):
        # Blend the image with a solid color overlay for a 'photo filter' effect
        overlay = Image.new("RGB", im.size, color)
        return Image.blend(im.convert("RGB"), overlay, alpha=density)

    @staticmethod
    def rotate(im, degrees):
        # Rotate image by degrees; expand=True keeps the full image visible
        return im.rotate(degrees, expand=True)

    @staticmethod
    def flip_horizontal(im):
        return ImageOps.mirror(im)

    @staticmethod
    def flip_vertical(im):
        return ImageOps.flip(im)

    @staticmethod
    def extract_red_channel(im):
        """Extract red channel and return as grayscale image."""
        rgb_im = im.convert("RGB")
        r, g, b = rgb_im.split()
        return r.convert("RGB")

    @staticmethod
    def extract_green_channel(im):
        """Extract green channel and return as grayscale image."""
        rgb_im = im.convert("RGB")
        r, g, b = rgb_im.split()
        return g.convert("RGB")

    @staticmethod
    def extract_blue_channel(im):
        """Extract blue channel and return as grayscale image."""
        rgb_im = im.convert("RGB")
        r, g, b = rgb_im.split()
        return b.convert("RGB")

    @staticmethod
    def grayscale_average(im):
        """
        Apply grayscale transformation using average method.
        Transformation function: s = (R + G + B) / 3
        """
        rgb_im = im.convert("RGB")
        width, height = rgb_im.size
        pixels = list(rgb_im.getdata())
        
        gray_pixels = []
        for r, g, b in pixels:
            # Apply transformation: s = (R + G + B) / 3
            gray_value = int((r + g + b) / 3)
            gray_pixels.append((gray_value, gray_value, gray_value))
        
        gray_im = Image.new("RGB", (width, height))
        gray_im.putdata(gray_pixels)
        return gray_im

    @staticmethod
    def get_channel_histogram(im, channel='R'):
        """
        Get histogram data for a specific channel.
        
        Args:
            im: PIL Image
            channel: 'R', 'G', or 'B'
        
        Returns:
            List of 256 values representing the histogram
        """
        rgb_im = im.convert("RGB")
        r, g, b = rgb_im.split()
        
        if channel == 'R':
            return r.histogram()
        elif channel == 'G':
            return g.histogram()
        elif channel == 'B':
            return b.histogram()
        else:
            raise ValueError("Channel must be 'R', 'G', or 'B'")

    @staticmethod
    def get_grayscale_histogram(im):
        """
        Get histogram data for grayscale image.
        
        Args:
            im: PIL Image (will be converted to grayscale)
        
        Returns:
            List of 256 values representing the histogram
        """
        gray_im = ImageOps.grayscale(im)
        return gray_im.histogram()