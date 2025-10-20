"""
Channel and Histogram Display Window
Shows RGB channels, their histograms, grayscale transformation, and its histogram
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
from .image_tools import ImageTools


class ChannelHistogramWindow:
    """Window for displaying RGB channels and histograms."""
    
    def __init__(self, parent, image):
        """
        Create channel and histogram window.
        
        Args:
            parent: Parent window
            image: PIL Image to analyze
        """
        self.window = tk.Toplevel(parent)
        self.window.title("RGB Channels and Histograms")
        self.window.geometry("700x900")
        self.window.configure(bg="#2b2b2b")
        
        self.image = image
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI components."""
        # Create main scrollable frame
        main_frame = tk.Frame(self.window, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas with scrollbar for scrolling
        canvas = tk.Canvas(main_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2b2b2b")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # --- RED CHANNEL SECTION ---
        self._add_section_title(scrollable_frame, "Red Channel")
        red_channel = ImageTools.extract_red_channel(self.image)
        self._add_image(scrollable_frame, red_channel, max_size=(280, 200))
        
        self._add_section_title(scrollable_frame, "Red Channel Histogram")
        red_hist = ImageTools.get_channel_histogram(self.image, 'R')
        red_hist_img = self._create_histogram_image(red_hist, color=(255, 0, 0))
        self._add_image(scrollable_frame, red_hist_img, max_size=(400, 180))
        
        # --- GREEN CHANNEL SECTION ---
        self._add_section_title(scrollable_frame, "Green Channel")
        green_channel = ImageTools.extract_green_channel(self.image)
        self._add_image(scrollable_frame, green_channel, max_size=(280, 200))
        
        self._add_section_title(scrollable_frame, "Green Channel Histogram")
        green_hist = ImageTools.get_channel_histogram(self.image, 'G')
        green_hist_img = self._create_histogram_image(green_hist, color=(0, 255, 0))
        self._add_image(scrollable_frame, green_hist_img, max_size=(400, 180))
        
        # --- BLUE CHANNEL SECTION ---
        self._add_section_title(scrollable_frame, "Blue Channel")
        blue_channel = ImageTools.extract_blue_channel(self.image)
        self._add_image(scrollable_frame, blue_channel, max_size=(280, 200))
        
        self._add_section_title(scrollable_frame, "Blue Channel Histogram")
        blue_hist = ImageTools.get_channel_histogram(self.image, 'B')
        blue_hist_img = self._create_histogram_image(blue_hist, color=(0, 0, 255))
        self._add_image(scrollable_frame, blue_hist_img, max_size=(400, 180))
        
        # --- GRAYSCALE TRANSFORMATION SECTION ---
        self._add_section_title(scrollable_frame, "Grayscale Transformation (s = (R + G + B) / 3)")
        gray_image = ImageTools.grayscale_average(self.image)
        self._add_image(scrollable_frame, gray_image, max_size=(280, 200))
        
        self._add_section_title(scrollable_frame, "Grayscale Histogram")
        gray_hist = ImageTools.get_grayscale_histogram(gray_image)
        gray_hist_img = self._create_histogram_image(gray_hist, color=(128, 128, 128))
        self._add_image(scrollable_frame, gray_hist_img, max_size=(400, 180))
    
    def _add_section_title(self, parent, title):
        """Add a section title."""
        label = tk.Label(
            parent,
            text=title,
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Arial", 12, "bold"),
            anchor="w",
            pady=5
        )
        label.pack(fill=tk.X, padx=5)
    
    def _add_image(self, parent, pil_image, max_size=(500, 500)):
        """Add an image to the display."""
        # Resize image if needed to fit in window
        img_copy = pil_image.copy()
        img_copy.thumbnail(max_size, Image.LANCZOS)
        
        # Create frame with border
        img_frame = tk.Frame(parent, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
        img_frame.pack(pady=5, padx=5)
        
        # Convert to PhotoImage and display
        photo = ImageTk.PhotoImage(img_copy)
        label = tk.Label(img_frame, image=photo, bg="#1a1a1a")
        label.image = photo  # Keep a reference
        label.pack(padx=2, pady=2)
    
    def _create_histogram_image(self, histogram_data, color=(255, 255, 255), width=400, height=150):
        """
        Create a visual representation of histogram data.
        
        Args:
            histogram_data: List of 256 values (frequency for each intensity level)
            color: RGB tuple for histogram bars
            width: Width of histogram image
            height: Height of histogram image
        
        Returns:
            PIL Image of the histogram
        """
        # Create black background
        img = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Find maximum value for normalization
        max_value = max(histogram_data) if max(histogram_data) > 0 else 1
        
        # Draw histogram bars
        bar_width = width / 256.0
        for i, value in enumerate(histogram_data):
            # Normalize height
            bar_height = int((value / max_value) * (height - 15))
            
            # Calculate bar position
            x0 = int(i * bar_width)
            x1 = int((i + 1) * bar_width)
            y0 = height - bar_height - 8
            y1 = height - 8
            
            # Draw bar
            draw.rectangle([x0, y0, x1, y1], fill=color)
        
        # Draw grid lines for reference
        # Horizontal lines
        for i in range(5):
            y = int(i * (height - 15) / 4) + 8
            draw.line([(0, y), (width, y)], fill=(40, 40, 40), width=1)
        
        # Vertical lines (at 0, 64, 128, 192, 255)
        for i in [0, 64, 128, 192, 255]:
            x = int(i * bar_width)
            draw.line([(x, 0), (x, height)], fill=(60, 60, 60), width=1)
        
        return img

