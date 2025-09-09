import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance, ImageOps
import os

# ---------------- Tooltip Widget ----------------
class ToolTip:
    """
    Small popup tooltip that appears when hovering over a widget.
    Used for toolbar buttons to show tooltips.
    """
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func  # function returning the tooltip text dynamically
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)  # show when mouse enters
        widget.bind("<Leave>", self.hide_tip)  # hide when mouse leaves

    def show_tip(self, event=None):
        # Only show if not already showing
        if self.tip_window:
            return
        text = self.text_func()
        if not text:
            return
        try:
            x, y, _, _ = self.widget.bbox("insert")
        except:
            x, y = 0, 0
        # Position near mouse
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # Create floating window
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  
        tw.wm_geometry(f"+{x}+{y}")
        # Label with text
        label = tk.Label(
            tw, text=text, background="#222", foreground="white",
            relief="solid", borderwidth=1, font=("Inter", 9)
        )
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# ---------------- Main App ----------------
class ImageViewerApp:
    """
    Main application class for the image viewer/editor.
    Handles all UI, image state, tools, and events.
    """
    def __init__(self, root):
        # --- Window setup ---
        self.root = root
        self.root.title("Image Processor")
        self.root.geometry("1100x720")
        self.root.configure(bg="#383838")

        # --- Image State ---
        self.original_image = None    # The main PIL image (all edits modify this)
        self.display_image_cache = None  # Cached resized image for display
        self.history = []             # List of previous states for undo/redo
        self.history_index = -1       # Current index in history
        self.max_history = 30         # Limit history size

        # --- View State ---
        self.zoom_level = 1.0         # Current zoom factor (1.0 = 100%)
        self.min_zoom = 0.1           # Minimum zoom (10%)
        self.max_zoom = 8.0           # Maximum zoom (800%)
        self._last_img_origin_x = 0   # Last drawn image origin (for mapping clicks)
        self._last_img_origin_y = 0
        self._last_display_size = (0,0)

        # --- Clipboard ---
        self.clipboard_image = None   # Stores a copied/cut image

        # --- Tools ---
        self.active_tool = None       # Current selected tool (move, zoom, eyedropper)
        self.hover_box = None         # Floating hover popup for eyedropper
        self.marker_id = None         # Circle marker drawn by eyedropper
        self.swatch_window = None     # Floating color info popup

        # --- Menus ---
        menubar = tk.Menu(self.root, bg="#504F4F", fg="white", tearoff=0, font=("Inter", 10))
        self.root.config(menu=menubar)

        # File menu (open/save/export/info)
        filemenu = tk.Menu(menubar, tearoff=0, bg="#504F4F", fg="white", font=("Inter", 10))
        filemenu.add_command(label="Open Image", command=self.open_image)
        filemenu.add_command(label="Save As", command=self.save_as)
        filemenu.add_command(label="Export", command=self.export_image)
        filemenu.add_command(label="File Info", command=self.show_file_info)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        # Edit menu (undo/redo + cut/copy/paste/clear)
        editmenu = tk.Menu(menubar, tearoff=0, bg="#504F4F", fg="white", font=("Inter", 10))
        editmenu.add_command(label="Undo (Ctrl+Z)", command=self.undo)
        editmenu.add_command(label="Redo (Shift+Ctrl+Z)", command=self.redo)
        editmenu.add_separator()
        editmenu.add_command(label="Cut (Ctrl+X)", command=self.cut)
        editmenu.add_command(label="Copy (Ctrl+C)", command=self.copy)
        editmenu.add_command(label="Paste (Ctrl+V)", command=self.paste)
        editmenu.add_command(label="Clear (Delete)", command=self.clear)
        menubar.add_cascade(label="Edit", menu=editmenu)

        # Image menu (adjustments + transform)
        imagemenu = tk.Menu(menubar, tearoff=0, bg="#504F4F", fg="white", font=("Inter", 10))
        adjustments = tk.Menu(imagemenu, tearoff=0, bg="#504F4F", fg="white", font=("Inter", 10))
        adjustments.add_command(label="Brightness/Contrast", command=self.adjust_brightness_contrast)
        adjustments.add_command(label="Black & White", command=self.black_and_white)
        adjustments.add_command(label="Invert", command=self.invert)
        adjustments.add_command(label="Photo Filter (Density)", command=self.photo_filter)
        imagemenu.add_cascade(label="Adjustments", menu=adjustments)

        transform = tk.Menu(imagemenu, tearoff=0, bg="#504F4F", fg="white", font=("Inter", 10))
        transform.add_command(label="Rotate 90° CCW", command=lambda: self.transform("ccw"))
        transform.add_command(label="Rotate 90° CW", command=lambda: self.transform("cw"))
        transform.add_command(label="Rotate 180°", command=lambda: self.transform("180"))
        transform.add_command(label="Flip Horizontal", command=lambda: self.transform("flip_h"))
        transform.add_command(label="Flip Vertical", command=lambda: self.transform("flip_v"))
        imagemenu.add_cascade(label="Transform", menu=transform)
        menubar.add_cascade(label="Image", menu=imagemenu)

        # View menu (zoom)
        viewmenu = tk.Menu(menubar, tearoff=0, bg="#504F4F", fg="white", font=("Inter", 10))
        viewmenu.add_command(label="Zoom In", command=self.zoom_in)
        viewmenu.add_command(label="Zoom Out", command=self.zoom_out)
        viewmenu.add_command(label="Reset Zoom", command=self.reset_zoom)
        menubar.add_cascade(label="View", menu=viewmenu)

        # --- Keyboard Shortcuts ---
        self.root.bind_all("<Control-z>", lambda e: self.undo())
        self.root.bind_all("<Control-Z>", lambda e: self.undo())
        self.root.bind_all("<Control-Shift-Z>", lambda e: self.redo())
        self.root.bind_all("<Control-y>", lambda e: self.redo())
        self.root.bind_all("<Control-c>", lambda e: self.copy())
        self.root.bind_all("<Control-x>", lambda e: self.cut())
        self.root.bind_all("<Control-v>", lambda e: self.paste())
        self.root.bind_all("<Delete>", lambda e: self.clear())

        # --- UI Layout ---
        self.main_frame = tk.Frame(self.root, bg="#383838")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Left toolbar (vertical) ---
        self.toolbar = tk.Frame(self.main_frame, width=68, bg="#232323", highlightbackground="#383838", highlightthickness=1)
        self.toolbar.pack(side=tk.LEFT, fill=tk.Y)
        self.toolbar.pack_propagate(False)

        # Toolbar button style for consistency
        toolbar_btn_style = {
            "relief": tk.FLAT,
            "bg": "#232323",
            "activebackground": "#353535",
            "bd": 0,
            "highlightthickness": 0,
            "font": ("Segoe UI", 11, "bold"),
            "fg": "#ffffff",
            "activeforeground": "#ffffff",
            "cursor": "hand2"
        }

        # Helper to highlight the active tool button
        def set_active(btn):
            for b in [self.move_btn, self.eyedropper_btn, self.zoom_btn]:
                b.config(bg="#232323")
            btn.config(bg="#353535")

        # Helper to load icons (returns None if not found)
        def load_icon(name):
            try:
                return ImageTk.PhotoImage(Image.open(name))
            except Exception:
                return None

        # Load icons for toolbar
        self.icon_move = load_icon("move.png")
        self.icon_eyedrop = load_icon("eyedropper.png")
        self.icon_zoom = load_icon("zoom.png")

        # Move tool button
        if self.icon_move:
            self.move_btn = tk.Button(self.toolbar, image=self.icon_move, command=lambda: [self.set_tool("move"), set_active(self.move_btn)], **toolbar_btn_style)
        else:
            self.move_btn = tk.Button(self.toolbar, text="Move", command=lambda: [self.set_tool("move"), set_active(self.move_btn)], **toolbar_btn_style)
        self.move_btn.pack(pady=(24, 16), padx=10, fill=tk.X)
        ToolTip(self.move_btn, lambda: "Move Tool")

        # Eyedropper tool button
        if self.icon_eyedrop:
            self.eyedropper_btn = tk.Button(self.toolbar, image=self.icon_eyedrop, command=lambda: [self.set_tool("eyedropper"), set_active(self.eyedropper_btn)], **toolbar_btn_style)
        else:
            self.eyedropper_btn = tk.Button(self.toolbar, text="Eyedropper", command=lambda: [self.set_tool("eyedropper"), set_active(self.eyedropper_btn)], **toolbar_btn_style)
        self.eyedropper_btn.pack(pady=16, padx=10, fill=tk.X)
        ToolTip(self.eyedropper_btn, lambda: "Eyedropper Tool")

        # Zoom tool button
        if self.icon_zoom:
            self.zoom_btn = tk.Button(self.toolbar, image=self.icon_zoom, command=lambda: [self.set_tool("zoom"), set_active(self.zoom_btn)], **toolbar_btn_style)
        else:
            self.zoom_btn = tk.Button(self.toolbar, text="Zoom", command=lambda: [self.set_tool("zoom"), set_active(self.zoom_btn)], **toolbar_btn_style)
        self.zoom_btn.pack(pady=16, padx=10, fill=tk.X)
        ToolTip(self.zoom_btn, lambda: "Zoom Tool")

        # Set default active tool highlight (move tool)
        set_active(self.move_btn)

        # --- Canvas frame (for image display) ---
        canvas_frame = tk.Frame(self.main_frame, bg="#383838")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbars for canvas
        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(canvas_frame, bg="#444444", highlightthickness=0,
                                xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Mouse bindings for canvas (scroll, click)
        self.canvas.bind("<MouseWheel>", self.mouse_zoom)  # Windows
        self.canvas.bind("<Button-4>", lambda e: self.mouse_zoom(e))  # Linux scroll up
        self.canvas.bind("<Button-5>", lambda e: self.mouse_zoom(e))  # Linux scroll down
        self.canvas.bind("<Button-1>", self.canvas_click)  # Left click (default, overridden by tools)

        # --- Home screen label (when no image loaded) ---
        self.home_frame = tk.Frame(self.canvas, bg="#383838")
        try:
            comp = Image.open("computer.png").resize((80, 80), Image.LANCZOS)
            self.home_icon = ImageTk.PhotoImage(comp)
        except Exception:
            self.home_icon = None

        self.home_label_image = tk.Label(self.home_frame, image=self.home_icon, bg="#383838", borderwidth=0, highlightthickness=0)
        self.home_label_text = tk.Label(
            self.home_frame, text="Open from Computer",
            bg="#383838", fg="#fafafa", font=("Segoe UI", 16, "bold")
        )
        self.home_button = tk.Button(
            self.home_frame, text="Browse...",
            command=self.open_image_dialog,
            bg="#444", fg="white", font=("Segoe UI", 12, "bold"), relief="flat", bd=0, padx=18, pady=6, cursor="hand2", activebackground="#555"
        )

        # Stack home screen widgets vertically, centered
        self.home_label_image.pack(pady=(32, 10))
        self.home_label_text.pack()
        self.home_button.pack(pady=18)

        self.show_home()  # Show home screen at startup

        # --- Status bar (bottom) ---
        self.status_frame = tk.Frame(self.root, bg="#504F4F")
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Zoom slider (mirrors zoom level)
        self.zoom_var = tk.IntVar(value=100)
        self.zoom_slider = tk.Scale(self.status_frame, from_=10, to=500, orient=tk.HORIZONTAL,
                                    variable=self.zoom_var, bg="#504F4F", fg="white", troughcolor="#383838",
                                    showvalue=True, command=self.set_zoom, length=150)
        self.zoom_slider.pack(side=tk.LEFT, padx=6, pady=4)

        # Status labels
        self.filename_label = tk.Label(self.status_frame, text="File: None", bg="#504F4F", fg="white", font=("Inter", 10))
        self.filename_label.pack(side=tk.LEFT, padx=10)
        self.zoom_label = tk.Label(self.status_frame, text="100%", bg="#504F4F", fg="white", font=("Inter", 10))
        self.zoom_label.pack(side=tk.RIGHT, padx=10)
        self.color_label = tk.Label(self.status_frame, text="Color: -", bg="#504F4F", fg="white", font=("Inter", 10))
        self.color_label.pack(side=tk.RIGHT, padx=10)

    # ---------- history helpers ----------
    def push_history(self, state_image):
        """
        Save the current state of the image into the history list.
        Used before making edits (so we can undo later).
        """
        # If we are in the middle of the history (after undo), cut off "future" states
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        # Append a copy of the image (or None if empty)
        if state_image is None:
            self.history.append(None)
        else:
            self.history.append(state_image.copy())

        # Keep history from growing too big (max_history)
        if len(self.history) > self.max_history:
            self.history.pop(0)  # drop oldest
        else:
            self.history_index += 1  # move pointer forward

        # Clamp index
        if self.history_index >= len(self.history):
            self.history_index = len(self.history) - 1

    def restore_from_history(self):
        """
        Restore image from history (used in undo/redo).
        Updates original_image to match saved history state.
        """
        if 0 <= self.history_index < len(self.history):
            state = self.history[self.history_index]
            if state is None:
                # If history state was empty (like after Clear)
                self.original_image = None
                self.canvas.delete("all")
                self.show_home()
                self.filename_label.config(text="File: None")
            else:
                # Otherwise restore saved image copy
                self.original_image = state.copy()
                self.display_image(center=True)

    # ---------- tools & events ----------
    def set_tool(self, tool_name):
        """
        Set the active tool (move, eyedropper, zoom) and bind the correct canvas events.
        """
        # Unbind all tool-specific canvas events first
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

        self.active_tool = tool_name
        self.color_label.config(text=f"Tool: {tool_name}")

        if tool_name == "move":
            # Move tool: drag to pan
            self.canvas.bind("<Button-1>", self._move_start)
            self.canvas.bind("<B1-Motion>", self._move_drag)
            self.canvas.bind("<ButtonRelease-1>", lambda e: None)
        elif tool_name == "eyedropper":
            # Eyedropper: click to pick color, show swatch
            self.canvas.bind("<Button-1>", self._eye_pick)
            self.canvas.bind("<B1-Motion>", lambda e: None)
            self.canvas.bind("<ButtonRelease-1>", lambda e: None)
        elif tool_name == "zoom":
            # Zoom tool: click to zoom in at the clicked point
            self.canvas.bind("<Button-1>", self._zoom_click)
            self.canvas.bind("<B1-Motion>", lambda e: None)
            self.canvas.bind("<ButtonRelease-1>", lambda e: None)
        else:
            # Default: no action
            self.canvas.bind("<Button-1>", lambda e: None)

    def _zoom_click(self, event):
        """
        When using the zoom tool, clicking the image zooms in at the clicked point.
        """
        if not self.original_image:
            return
        self.zoom_at(event.x, event.y, 1.25)

    # ---------- Move tool handlers ----------
    def _move_start(self, event):
        """
        Start panning the image (move tool).
        """
        self.canvas.scan_mark(event.x, event.y)

    def _move_drag(self, event):
        """
        Pan the image as the mouse moves (move tool).
        """
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    # ---------- Eyedropper handlers ----------
    def _eye_pick(self, event):
        """
        Pick a color from the image (eyedropper tool).
        Shows a marker and a floating color swatch.
        """
        if not self.original_image:
            return

        # Convert canvas click to image pixel coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = int((canvas_x - self._last_img_origin_x) / self.zoom_level)
        img_y = int((canvas_y - self._last_img_origin_y) / self.zoom_level)

        if img_x < 0 or img_y < 0 or img_x >= self.original_image.width or img_y >= self.original_image.height:
            return

        rgb = self.original_image.convert("RGB").getpixel((img_x, img_y))
        hexc = "#%02x%02x%02x" % rgb
        cmyk = self.rgb_to_cmyk(*rgb)
        # Draw marker at the picked pixel
        r = 6
        if self.marker_id:
            try:
                self.canvas.delete(self.marker_id)
            except Exception:
                pass
        self.marker_id = self.canvas.create_oval(
            canvas_x - r, canvas_y - r, canvas_x + r, canvas_y + r,
            outline="#000000", width=2, fill=hexc
        )

        # Show floating swatch near cursor
        self.show_color_swatch(event.x_root, event.y_root, rgb, hexc, cmyk)
        self.color_label.config(text=f"Color: {hexc}  RGB:{rgb}")
    
    def show_color_swatch(self, root_x, root_y, rgb, hexc, cmyk):
        """
        Show a floating color swatch popup near the mouse with HEX, RGB, and CMYK values.
        """
        if self.swatch_window:
            try:
                self.swatch_window.destroy()
            except Exception:
                pass

        sw = tk.Toplevel(self.root)
        sw.wm_overrideredirect(True)
        sw.geometry(f"+{root_x + 16}+{root_y + 8}")
        sw.config(bg="#222", padx=6, pady=6)

        block = tk.Frame(sw, width=44, height=44, bg=hexc, relief=tk.SUNKEN, bd=1)
        block.pack(side=tk.LEFT, padx=(0,8))

        txt = f"{hexc}\nRGB: {rgb}\nCMYK: {cmyk}"
        lbl = tk.Label(sw, text=txt, bg="#222", fg="white", justify=tk.LEFT, font=("Arial", 9))
        lbl.pack(side=tk.LEFT)

        self.swatch_window = sw
        sw.after(1800, lambda: (sw.destroy(), setattr(self, 'swatch_window', None)))

    def canvas_click(self, event):
        """
        Handles clicks on the canvas depending on the selected tool.
        (Fallback handler, not used when a tool is active.)
        """
        if not self.original_image:
            return

        if self.active_tool == "eyedropper":
            # Convert from canvas coords -> image coords
            img_x = (self.canvas.canvasx(event.x) - self._last_img_origin_x) / self.zoom_level
            img_y = (self.canvas.canvasy(event.y) - self._last_img_origin_y) / self.zoom_level

            try:
                img_x_i = int(img_x)
                img_y_i = int(img_y)

                # Prevent clicks outside image
                if img_x_i < 0 or img_y_i < 0:
                    return
                if img_x_i >= self.original_image.width or img_y_i >= self.original_image.height:
                    return

                # Get pixel color
                rgb = self.original_image.convert("RGB").getpixel((img_x_i, img_y_i))
                hex_color = "#%02x%02x%02x" % rgb
                cmyk = self.rgb_to_cmyk(*rgb)

                # Show floating hover box with color info
                self.show_hover_info(event.x_root, event.y_root, rgb, hex_color, cmyk)

                # Update status bar
                self.color_label.config(text=f"Color: {hex_color}")
            except Exception:
                pass

        elif self.active_tool == "zoom":
            # Zoom in when clicked
            self.zoom_at(event.x, event.y, 1.25)

        elif self.active_tool == "move":
            # TODO: could implement drag/pan later
            pass

    def show_hover_info(self, x, y, rgb, hex_color, cmyk):
        """
        Display a floating popup (tooltip-like) with color values.
        Appears where you clicked with eyedropper.
        Shows HEX, RGB, CMYK.
        """
        # Remove old popup if it exists
        if self.hover_box:
            self.hover_box.destroy()

        self.hover_box = tk.Toplevel(self.root)
        self.hover_box.wm_overrideredirect(True)  # remove window decorations
        self.hover_box.wm_geometry(f"+{x+15}+{y+15}")  # place near mouse
        text = f"HEX: {hex_color}\nRGB: {rgb}\nCMYK: {cmyk}"
        tk.Label(self.hover_box, text=text, bg="#222", fg="white", font=("Inter", 9),
                 relief="solid", borderwidth=1).pack()

        # Auto-hide after 1.5s
        self.root.after(1500, self.clear_hover)

    def clear_hover(self):
        """Close floating hover box (used with eyedropper)."""
        if self.hover_box:
            self.hover_box.destroy()
            self.hover_box = None

    def mouse_zoom(self, event):
        """
        Zoom with the mouse wheel.
        - Windows: event.delta is ±120
        - Linux: uses Button-4 / Button-5
        """
        delta = 0
        if hasattr(event, "delta"):
            delta = event.delta
        elif event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120

        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    # ---------- zoom / display ----------
    def set_zoom(self, val):
        """
        When the zoom slider changes, update zoom level.
        Slider goes from 10 to 500 (%).
        This doesn’t change the actual image, just the view.
        """
        try:
            z = int(val) / 100.0
        except Exception:
            return

        # Clamp zoom between 10% and 1000%
        self.zoom_level = max(0.1, min(10.0, z))
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")
        self.zoom_var.set(int(self.zoom_level*100))
        self.display_image(center=False)

    def zoom_in(self):
        """Zoom in by 25%."""
        self.zoom_level = min(self.zoom_level * 1.25, 10.0)
        self.zoom_var.set(int(self.zoom_level * 100))
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")
        self.display_image(center=False)

    def zoom_out(self):
        """Zoom out by 25%."""
        self.zoom_level = max(self.zoom_level / 1.25, 0.1)
        self.zoom_var.set(int(self.zoom_level * 100))
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")
        self.display_image(center=False)

    def reset_zoom(self):
        """Reset zoom to 100% and center the image."""
        self.zoom_level = 1.0
        self.zoom_var.set(100)
        self.zoom_label.config(text="100%")
        self.display_image(center=True)

    def zoom_at(self, canvas_x, canvas_y, factor):
        """
        Zoom in at the clicked point (used with Zoom Tool).
        Keeps the clicked point at roughly the same position after zoom.
        """
        # Convert canvas coords -> image coords
        img_x = (self.canvas.canvasx(canvas_x) - self._last_img_origin_x) / self.zoom_level
        img_y = (self.canvas.canvasy(canvas_y) - self._last_img_origin_y) / self.zoom_level

        # Update zoom level
        self.zoom_level = max(0.1, min(10.0, self.zoom_level * factor))
        self.zoom_var.set(int(self.zoom_level * 100))
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")
        self.display_image(center=False)

        # Try to keep the same point in view
        new_canvas_x = img_x * self.zoom_level + self._last_img_origin_x
        new_canvas_y = img_y * self.zoom_level + self._last_img_origin_y
        dx = new_canvas_x - canvas_x
        dy = new_canvas_y - canvas_y
        self.canvas.xview_scroll(int(dx), "units")
        self.canvas.yview_scroll(int(dy), "units")

    def get_display_image(self):
        """
        Create a resized image for the current zoom level.
        Doesn’t change the original image.
        Returns a new PIL image (scaled).
        """
        if not self.original_image:
            return None
        w, h = self.original_image.size
        new_w = max(1, int(round(w * self.zoom_level)))
        new_h = max(1, int(round(h * self.zoom_level)))
        return self.original_image.resize((new_w, new_h), Image.LANCZOS)

    def display_image(self, center=False):
        """
        Actually draw the image on the canvas.
        Uses the zoom level to resize first.
        Centers image if smaller than canvas.
        Otherwise aligns to top-left (scrollbars handle panning).
        """
        self.canvas.delete("all")

        if not self.original_image:
            # Show "Open from Computer" message if no image
            self.show_home()
            return

        disp_img = self.get_display_image()
        self.tk_image = ImageTk.PhotoImage(disp_img)

        # Get canvas + image size
        canvas_w = self.canvas.winfo_width() or self.canvas.winfo_reqwidth()
        canvas_h = self.canvas.winfo_height() or self.canvas.winfo_reqheight()
        img_w, img_h = disp_img.size

        # Compute top-left (center if small, else align)
        if center or (img_w < canvas_w and img_h < canvas_h):
            x = max(0, (canvas_w - img_w) // 2)
            y = max(0, (canvas_h - img_h) // 2)
        else:
            x = 0
            y = 0

        # Save info for eyedropper/zoom
        self._last_img_origin_x = x
        self._last_img_origin_y = y
        self._last_display_size = (img_w, img_h)

        # Draw
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.tk_image)

        # Update scrollbars
        self.canvas.config(scrollregion=(0, 0, x + img_w, y + img_h))

        # Hide home label since we have an image now
        self.hide_home()

    # ---------- file ops & edits ----------
    def open_image(self):
        """
        Opens an image file from computer.
        Uses file dialog to select a file.
        Loads the image with PIL and makes it the 'original_image'.
        Resets history and zoom.
        Hides the home screen once an image is loaded.
        """
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tiff *.bmp")]
        )
        if not file_path:
            return  # user cancelled

        try:
            opened = Image.open(file_path)  # load with PIL
        except Exception as e:
            messagebox.showerror("Open Error", f"Could not open image:\n{e}")
            return

        # Convert to RGB or RGBA so we can safely edit
        self.original_image = (
            opened.convert("RGBA") if opened.mode in ("RGBA", "LA") else opened.convert("RGB")
        )

        # Reset history
        self.history = []
        self.history_index = -1
        self.push_history(self.original_image)
        self.history_index = 0  # ensure index is correct after first push

        # Reset zoom to 100%
        self.zoom_level = 1.0
        self.zoom_var.set(100)
        self.zoom_label.config(text="100%")

        # Show image on canvas, centered
        self.display_image(center=True)

        # Update status bar with filename
        self.filename_label.config(text=f"File: {os.path.basename(file_path)}")

        # Hide home landing screen
        self.hide_home()

    def save_as(self):
        """
        Save the current image with a new filename (Save As).
        Always asks where to save.
        Saves as PNG or JPG.
        """
        if not self.original_image:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
        )
        if not file_path:
            return  # user cancelled

        # Ensure we save in RGB (JPG does not support alpha)
        save_img = self.original_image.convert("RGB")
        save_img.save(file_path)

    def export_image(self):
        """
        Export the current image (like Save As but defaults to JPG).
        """
        if not self.original_image:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
        )
        if not file_path:
            return

        save_img = self.original_image.convert("RGB")
        save_img.save(file_path)

    def show_file_info(self):
        """
        Show basic info about the current image in a popup:
        - Width x Height in pixels.
        """
        if self.original_image:
            file_info = f"Size: {self.original_image.size[0]}x{self.original_image.size[1]} pixels"
            messagebox.showinfo("File Info", file_info)
        else:
            messagebox.showinfo("File Info", "No image loaded.")

    # ---------- edits (operate on original_image) ----------
    def apply_and_push(self, func):
        """
        Helper function for edits:
        Push current image to history (so undo works).
        Run the edit function (func).
        Update original_image and refresh display.
        """
        if not self.original_image:
            return

        self.push_history(self.original_image)
        try:
            new_img = func(self.original_image)
            self.original_image = new_img
            self.display_image(center=True)
        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not apply edit:\n{e}")

    def invert(self):
        """Invert the colors (like a negative photo)."""
        self.apply_and_push(lambda im: ImageOps.invert(im.convert("RGB")))

    def adjust_brightness_contrast(self):
        """
        Slightly brighten and increase contrast.
        Uses PIL ImageEnhance.
        """
        self.apply_and_push(lambda im: ImageEnhance.Brightness(im).enhance(1.2).convert("RGB"))
        self.apply_and_push(lambda im: ImageEnhance.Contrast(im).enhance(1.2).convert("RGB"))

    def black_and_white(self):
        """Convert image to grayscale (black and white)."""
        self.apply_and_push(lambda im: ImageOps.grayscale(im).convert("RGB"))

    def photo_filter(self):
        """
        Apply a light orange filter (like a warming filter).
        Uses Image.blend with an orange overlay.
        """
        def _filter(im):
            overlay = Image.new("RGB", im.size, (255, 165, 0))  # orange
            return Image.blend(im.convert("RGB"), overlay, alpha=0.2)
        self.apply_and_push(_filter)

    def transform(self, action):
        """
        Rotate or flip the image depending on action string.
        """
        def _t(im):
            if action == "ccw":      # rotate 90 counter-clockwise
                return im.rotate(90, expand=True)
            if action == "cw":       # rotate 90 clockwise
                return im.rotate(-90, expand=True)
            if action == "180":      # rotate 180
                return im.rotate(180, expand=True)
            if action == "flip_h":   # flip horizontally
                return ImageOps.mirror(im)
            if action == "flip_v":   # flip vertically
                return ImageOps.flip(im)
            return im
        self.apply_and_push(_t)

    # ---------- edit actions: copy/paste/cut/clear ----------
    def copy(self):
        """
        Copy the current image to internal memory (clipboard).
        """
        if self.original_image:
            self.clipboard_image = self.original_image.copy()
            self.color_label.config(text="Color: Copied")
        else:
            self.color_label.config(text="Color: -")

    def paste(self):
        """
        Paste the last copied image into the viewer.
        Replaces the current image.
        """
        if self.clipboard_image:
            self.push_history(self.original_image)
            self.original_image = self.clipboard_image.copy()
            self.display_image(center=True)
            self.filename_label.config(text="File: (pasted)")
        else:
            messagebox.showinfo("Paste", "Clipboard is empty.")

    def cut(self):
        """
        Cut = Copy + Clear.
        Saves current image to clipboard.
        Then clears the canvas.
        """
        if self.original_image:
            self.copy()
            self.clear()

    def clear(self):
        """
        Remove the current image (like deleting it).
        This is undoable.
        Shows the home landing screen again.
        """
        if self.original_image:
            # push current state into history for undo
            self.push_history(self.original_image)

        # clear out current image
        self.original_image = None
        self.canvas.delete("all")

        # reset status bar
        self.filename_label.config(text="File: None")
        self.color_label.config(text="Color: -")
        self.zoom_var.set(100)
        self.zoom_label.config(text="100%")

        # show landing page again
        self.show_home()

    # ---------- undo / redo ----------
    def undo(self):
        """
        Undo the last action.
        Moves one step back in history.
        """
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_from_history()

    def redo(self):
        """
        Redo (go forward in history).
        Moves one step forward if available.
        """
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_from_history()

    # ---------- Home screen ----------
    def show_home(self):
        """
        Show landing screen (home screen) when no image is loaded.
        """
        self.canvas.delete("all")
        self.home_frame.place(relx=0.5, rely=0.5, anchor="center")

    def hide_home(self):
        """
        Hide landing screen when an image is opened.
        """
        self.home_frame.place_forget()

    def open_image_dialog(self):
        """
        Wrapper for the Browse button to open an image.
        """
        self.open_image()

    # ---------- util ----------
    def rgb_to_cmyk(self, r, g, b):
        """
        Convert an RGB color to CMYK values (0-100).
        Used in eyedropper tool.
        """
        if (r, g, b) == (0, 0, 0):
            return (0, 0, 0, 100)  # pure black

        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255
        min_cmy = min(c, m, y)

        # Avoid division by zero
        denom = (1 - min_cmy) if (1 - min_cmy) != 0 else 1
        c = (c - min_cmy) / denom
        m = (m - min_cmy) / denom
        y = (y - min_cmy) / denom
        k = min_cmy

        return (int(c * 100), int(m * 100), int(y * 100), int(k * 100))

# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.mainloop()