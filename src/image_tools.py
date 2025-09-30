"""
Image manipulation tools using PIL
"""
from PIL import Image, ImageOps, ImageEnhance


class ImageTools:
    """Static helper functions performing PIL-based edits returning new PIL Images."""
    
    @staticmethod
    def invert(im):
        return ImageOps.invert(im.convert("RGB"))

    @staticmethod
    def to_grayscale(im):
        return ImageOps.grayscale(im).convert("RGB")

    @staticmethod
    def brightness(im, factor):
        return ImageEnhance.Brightness(im).enhance(factor).convert("RGB")

    @staticmethod
    def contrast(im, factor):
        return ImageEnhance.Contrast(im).enhance(factor).convert("RGB")

    @staticmethod
    def photo_filter(im, color=(255, 165, 0), density=0.2):
        overlay = Image.new("RGB", im.size, color)
        return Image.blend(im.convert("RGB"), overlay, alpha=density)

    @staticmethod
    def rotate(im, degrees):
        return im.rotate(degrees, expand=True)

    @staticmethod
    def flip_horizontal(im):
        return ImageOps.mirror(im)

    @staticmethod
    def flip_vertical(im):
        return ImageOps.flip(im)
