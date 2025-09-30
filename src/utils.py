"""
Utility classes for image processing and management
"""
import colorsys


class ImageHistory:
    """Simple undo/redo stack manager for PIL Images."""
    def __init__(self, max_size=30):
        self.max_size = max_size
        self.stack = []
        self.index = -1

    def push(self, pil_image):
        # drop future states if we've undone
        if self.index < len(self.stack) - 1:
            self.stack = self.stack[: self.index + 1]
        self.stack.append(pil_image.copy() if pil_image is not None else None)
        if len(self.stack) > self.max_size:
            self.stack.pop(0)
        else:
            self.index += 1
        # clamp
        self.index = max(0, min(self.index, len(self.stack) - 1))

    def can_undo(self):
        return self.index > 0

    def can_redo(self):
        return self.index < len(self.stack) - 1

    def undo(self):
        if self.can_undo():
            self.index -= 1
            return self.stack[self.index]
        return None

    def redo(self):
        if self.can_redo():
            self.index += 1
            return self.stack[self.index]
        return None

    def reset(self):
        self.stack = []
        self.index = -1


class ColorUtils:
    """Color conversion helpers."""

    @staticmethod
    def rgb_to_hex(rgb):
        r, g, b = rgb
        return "#%02x%02x%02x" % (r, g, b)

    @staticmethod
    def rgb_to_cmyk(r, g, b):
        if (r, g, b) == (0, 0, 0):
            return (0, 0, 0, 100)
        c = 1 - r / 255.0
        m = 1 - g / 255.0
        y = 1 - b / 255.0
        min_cmy = min(c, m, y)
        denom = (1 - min_cmy) if (1 - min_cmy) != 0 else 1
        c = (c - min_cmy) / denom
        m = (m - min_cmy) / denom
        y = (y - min_cmy) / denom
        k = min_cmy
        return (int(c * 100), int(m * 100), int(y * 100), int(k * 100))

    @staticmethod
    def rgb_to_hsv_hsl(r, g, b):
        # normalize
        rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
        h_hsv, s_hsv, v = colorsys.rgb_to_hsv(rn, gn, bn)
        h_hsl, l, s_hsl = colorsys.rgb_to_hls(rn, gn, bn)  
        hsv = (int(round(h_hsv * 360)), int(round(s_hsv * 100)), int(round(v * 100)))
        hsl = (int(round(h_hsl * 360)), int(round(s_hsl * 100)), int(round(l * 100)))
        return hsv, hsl
