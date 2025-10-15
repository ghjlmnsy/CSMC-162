"""
PCX Information Display Window
Shows PCX header information, color palette, and image in a dedicated window
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class PCXInfoWindow:
    """Window for displaying PCX file information."""
    
    def __init__(self, parent, pcx_reader):
        """
        Create PCX info window.
        
        Args:
            parent: Parent window
            pcx_reader: PCXReader instance with loaded PCX file
        """
        self.window = tk.Toplevel(parent)
        self.window.title("PCX File Information")
        self.window.geometry("600x800")
        self.window.configure(bg="#2b2b2b")
        
        self.pcx_reader = pcx_reader
        self.header = pcx_reader.header
        
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
        
        # --- Original Image Section ---
        self._add_section_title(scrollable_frame, "Original Image")
        self._add_image(scrollable_frame, self.pcx_reader.image, max_size=(550, 400))
        
        # --- PCX Header Information Section ---
        self._add_section_title(scrollable_frame, "PCX Header Information")
        self._add_header_info(scrollable_frame)
        
        # --- Color Palette Section ---
        if self.pcx_reader.palette:
            self._add_section_title(scrollable_frame, "Color Palette")
            palette_img = self.pcx_reader.get_palette_image(cell_size=12)
            if palette_img:
                self._add_image(scrollable_frame, palette_img, max_size=(192, 192))
        else:
            # Note for images without palette (grayscale)
            if self.header.bits_per_pixel == 8 and self.header.num_planes == 1:
                self._add_section_title(scrollable_frame, "Image Type")
                note_frame = tk.Frame(scrollable_frame, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
                note_frame.pack(fill=tk.X, padx=5, pady=10)
                note_label = tk.Label(
                    note_frame,
                    text="This is a grayscale image (no color palette)",
                    bg="#1a1a1a",
                    fg="#aaaaaa",
                    font=("Arial", 10),
                    pady=10
                )
                note_label.pack(padx=10)
    
    def _add_section_title(self, parent, title):
        """Add a section title."""
        label = tk.Label(
            parent,
            text=title,
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Arial", 14, "bold"),
            anchor="w",
            pady=10
        )
        label.pack(fill=tk.X, padx=5)
    
    def _add_image(self, parent, pil_image, max_size=(500, 500)):
        """Add an image to the display."""
        # Resize image if needed to fit in window
        img_copy = pil_image.copy()
        img_copy.thumbnail(max_size, Image.LANCZOS)
        
        # Create frame with border
        img_frame = tk.Frame(parent, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
        img_frame.pack(pady=10, padx=5)
        
        # Convert to PhotoImage and display
        photo = ImageTk.PhotoImage(img_copy)
        label = tk.Label(img_frame, image=photo, bg="#1a1a1a")
        label.image = photo  # Keep a reference
        label.pack(padx=2, pady=2)
    
    def _add_header_info(self, parent):
        """Add PCX header information in a formatted display."""
        # Create frame for header info
        info_frame = tk.Frame(parent, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
        info_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Define header information fields
        fields = [
            ("Manufacturer:", f"Zsoft .pcx ({self.header.manufacturer})"),
            ("Version:", self.header.version),
            ("Encoding:", self.header.encoding),
            ("Bits per Pixel:", self.header.bits_per_pixel),
            ("Image Dimensions:", f"{self.header.xmin} {self.header.ymin} {self.header.xmax} {self.header.ymax}"),
            ("HDPI:", self.header.hdpi),
            ("VDPI:", self.header.vdpi),
            ("Number of Color Planes:", self.header.num_planes),
            ("Bytes per Line:", self.header.bytes_per_line),
            ("Palette Information:", self.header.palette_info),
            ("Horizontal Screen Size:", self.header.hscreen_size),
            ("Vertical Screen Size:", self.header.vscreen_size),
        ]
        
        # Add each field
        for i, (label_text, value) in enumerate(fields):
            row_frame = tk.Frame(info_frame, bg="#1a1a1a")
            row_frame.pack(fill=tk.X, padx=10, pady=2)
            
            label = tk.Label(
                row_frame,
                text=label_text,
                bg="#1a1a1a",
                fg="#aaaaaa",
                font=("Arial", 10),
                anchor="w",
                width=25
            )
            label.pack(side=tk.LEFT)
            
            value_label = tk.Label(
                row_frame,
                text=str(value),
                bg="#1a1a1a",
                fg="#ffffff",
                font=("Arial", 10),
                anchor="w"
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
