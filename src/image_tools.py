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
