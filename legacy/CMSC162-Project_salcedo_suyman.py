"""
SALCEDO, CHRIS SAMUEL 2022-05055
SUYMAN, ANN JUNAH 2022-09089


PROJECT 1:
A simple image viewer/editor with basic Photoshop-like features using Tkinter and PIL.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageOps
import colorsys
import os

# ---------------- Utility Classes ----------------
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

# ---------------- Tooltip (small helper) ----------------
class ToolTip:
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window:
            return
        text = self.text_func()
        if not text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(tw, text=text, bg="#222", fg="white", padx=6, pady=3, font=("Arial", 9))
        lbl.pack()

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# ---------------- Main App ----------------
class ImageViewerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Mini Image Editor")
        self.root.geometry("1100x720")
        self.root.configure(bg="#383838")

        # state
        self.original_image = None
        self.history = ImageHistory(max_size=40)
        self.clipboard_image = None

        # view params
        self.zoom_level = 1.0
        self._last_img_origin_x = 0
        self._last_img_origin_y = 0

        # tools & UI
        self.active_tool = None
        self.marker_id = None
        self.swatch_window = None
        self.hover_box = None

        # Load icons for toolbar
        def load_icon(filename):
            try:
                img = Image.open(filename).resize((28, 28), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                return None

        self.icon_move = load_icon("move.png")
        self.icon_eyedrop = load_icon("eyedropper.png")
        self.icon_zoom = load_icon("zoom.png")
        self.icon_brush = load_icon("brush.png")
        self.icon_eraser = load_icon("eraser.png")

        # Home screen icon
        try:
            comp = Image.open("computer.png").resize((80, 80), Image.LANCZOS)
            self.home_icon = ImageTk.PhotoImage(comp)
        except Exception:
            self.home_icon = None

        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()

    # ---------- UI construction ----------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        # File
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.open_image)
        filemenu.add_command(label="Save As", command=self.save_as)
        filemenu.add_command(label="Export", command=self.export_image)
        filemenu.add_command(label="File Info", command=self.show_file_info)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        # Edit
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Undo (Ctrl+Z)", command=self.undo)
        editmenu.add_command(label="Redo (Shift+Ctrl+Z)", command=self.redo)
        editmenu.add_separator()
        editmenu.add_command(label="Cut (Ctrl+X)", command=self.cut)
        editmenu.add_command(label="Copy (Ctrl+C)", command=self.copy)
        editmenu.add_command(label="Paste (Ctrl+V)", command=self.paste)
        editmenu.add_command(label="Clear (Delete)", command=self.clear)
        menubar.add_cascade(label="Edit", menu=editmenu)
        # Image
        imagemenu = tk.Menu(menubar, tearoff=0)
        adjustments = tk.Menu(imagemenu, tearoff=0)
        adjustments.add_command(label="Brightness/Contrast", command=self.adjust_brightness_contrast)
        adjustments.add_command(label="Black & White", command=self.black_and_white)
        adjustments.add_command(label="Invert", command=self.invert)
        adjustments.add_command(label="Photo Filter (Density)", command=self.photo_filter_dialog)
        imagemenu.add_cascade(label="Adjustments", menu=adjustments)
        transform = tk.Menu(imagemenu, tearoff=0)
        transform.add_command(label="Rotate 90° CCW", command=lambda: self.transform("ccw"))
        transform.add_command(label="Rotate 90° CW", command=lambda: self.transform("cw"))
        transform.add_command(label="Rotate 180°", command=lambda: self.transform("180"))
        transform.add_command(label="Flip Horizontal", command=lambda: self.transform("flip_h"))
        transform.add_command(label="Flip Vertical", command=lambda: self.transform("flip_v"))
        imagemenu.add_cascade(label="Transform", menu=transform)
        menubar.add_cascade(label="Image", menu=imagemenu)
        # View
        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Zoom In", command=self.zoom_in)
        viewmenu.add_command(label="Zoom Out", command=self.zoom_out)
        viewmenu.add_command(label="Reset Zoom", command=self.reset_zoom)
        menubar.add_cascade(label="View", menu=viewmenu)

        self.root.config(menu=menubar)

    def _build_layout(self):
        # Main frame for the app
        main_frame = tk.Frame(self.root, bg="#383838")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Toolbar on the left ---
        toolbar = tk.Frame(main_frame, width=68, bg="#232323")
        toolbar.pack(side=tk.LEFT, fill=tk.Y)
        toolbar.pack_propagate(False)
        btn_style = {"relief": tk.FLAT, "bg": "#232323", "fg": "white", "activebackground": "#353535", "bd": 0, "cursor": "hand2"}

        # Move tool button
        self.move_btn = tk.Button(toolbar, image=self.icon_move, compound=tk.LEFT, command=lambda: self.set_tool("move"), **btn_style)
        self.move_btn.pack(pady=(24, 12), padx=6, fill=tk.X)
        ToolTip(self.move_btn, lambda: "Move Tool")
        # Eyedropper tool button
        self.eyedropper_btn = tk.Button(toolbar, image=self.icon_eyedrop, compound=tk.LEFT, command=lambda: self.set_tool("eyedropper"), **btn_style)
        self.eyedropper_btn.pack(pady=12, padx=6, fill=tk.X)
        ToolTip(self.eyedropper_btn, lambda: "Eyedropper Tool")
        # Zoom tool button
        self.zoom_btn = tk.Button(toolbar, image=self.icon_zoom, compound=tk.LEFT, command=lambda: self.set_tool("zoom"), **btn_style)
        self.zoom_btn.pack(pady=12, padx=6, fill=tk.X)
        ToolTip(self.zoom_btn, lambda: "Zoom Tool")
        # Brush tool button
        self.brush_btn = tk.Button(toolbar, image=self.icon_brush, compound=tk.LEFT, command=lambda: self.set_tool("brush"), **btn_style)
        self.brush_btn.pack(pady=12, padx=6, fill=tk.X)
        ToolTip(self.brush_btn, lambda: "Brush Tool")
        # Eraser tool button
        self.eraser_btn = tk.Button(toolbar, image=self.icon_eraser, compound=tk.LEFT, command=lambda: self.set_tool("eraser"), **btn_style)
        self.eraser_btn.pack(pady=12, padx=6, fill=tk.X)
        ToolTip(self.eraser_btn, lambda: "Eraser Tool")

        # --- Canvas and scrollbars ---
        canvas_frame = tk.Frame(main_frame, bg="#383838")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(canvas_frame, bg="#444444", xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Mouse wheel and scroll bindings
        self.canvas.bind("<MouseWheel>", self._mouse_wheel)  # windows
        self.canvas.bind("<Button-4>", self._mouse_wheel)    # linux scroll up
        self.canvas.bind("<Button-5>", self._mouse_wheel)    # linux scroll down

        # --- Home screen label (when no image loaded) ---
        self.home_frame = tk.Frame(self.canvas, bg="#383838")
        self.home_label_image = tk.Label(self.home_frame, image=self.home_icon, bg="#383838", borderwidth=0, highlightthickness=0)
        self.home_label_text = tk.Label(
            self.home_frame, text="Open from Computer",
            bg="#383838", fg="#fafafa", font=("Inter", 16, "bold")
        )
        self.home_button = tk.Button(
            self.home_frame, text="Browse...",
            command=self.open_image,
            bg="#444", fg="white", font=("Inter", 12, "bold"), relief="flat", bd=0, padx=18, pady=6, cursor="hand2", activebackground="#555"
        )
        self.home_label_image.pack(pady=(24, 8))
        self.home_label_text.pack()
        self.home_button.pack(pady=12)

        self.show_home()

        # --- Status bar at the bottom ---
        status_frame = tk.Frame(self.root, bg="#504F4F")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        # Zoom slider
        self.zoom_var = tk.IntVar(value=100)
        self.zoom_slider = tk.Scale(status_frame, from_=10, to=500, orient=tk.HORIZONTAL, variable=self.zoom_var, command=self._slider_zoom, length=150)
        self.zoom_slider.pack(side=tk.LEFT, padx=6, pady=4)
        # Filename label
        self.filename_label = tk.Label(status_frame, text="File: None", bg="#504F4F", fg="white")
        self.filename_label.pack(side=tk.LEFT, padx=8)
        # --- Image size controls (width x height + resize button) ---
        tk.Label(status_frame, text="Size:", bg="#504F4F", fg="white").pack(side=tk.LEFT, padx=(16,2))
        self.size_w_var = tk.StringVar(value="-")
        self.size_h_var = tk.StringVar(value="-")
        self.size_w_entry = tk.Entry(status_frame, textvariable=self.size_w_var, width=5)
        self.size_h_entry = tk.Entry(status_frame, textvariable=self.size_h_var, width=5)
        self.size_w_entry.pack(side=tk.LEFT)
        tk.Label(status_frame, text="x", bg="#504F4F", fg="white").pack(side=tk.LEFT)
        self.size_h_entry.pack(side=tk.LEFT)
        self.resize_btn = tk.Button(status_frame, text="Resize", command=self._resize_image, bg="#666", fg="white", font=("Arial", 9), padx=6, pady=2)
        self.resize_btn.pack(side=tk.LEFT, padx=(4,12))
        # Zoom and color labels
        self.zoom_label = tk.Label(status_frame, text="100%", bg="#504F4F", fg="white")
        self.zoom_label.pack(side=tk.RIGHT, padx=8)
        self.color_label = tk.Label(status_frame, text="Color: -", bg="#504F4F", fg="white")
        self.color_label.pack(side=tk.RIGHT, padx=8)

    def _update_size_fields(self):
        if self.original_image:
            w, h = self.original_image.size
            self.size_w_var.set(str(w))
            self.size_h_var.set(str(h))
        else:
            self.size_w_var.set("-")
            self.size_h_var.set("-")

    def _resize_image(self):
        if not self.original_image:
            return
        try:
            w = int(self.size_w_var.get())
            h = int(self.size_h_var.get())
            if w < 1 or h < 1:
                raise ValueError
        except Exception:
            messagebox.showerror("Resize Error", "Please enter valid width and height.")
            return
        self.history.push(self.original_image)
        self.original_image = self.original_image.resize((w, h), Image.LANCZOS)
        self._display_image(center=True)
        self._update_size_fields()

    def _bind_shortcuts(self):
        self.root.bind_all("<Control-z>", lambda e: self.undo())
        self.root.bind_all("<Control-Z>", lambda e: self.undo())
        self.root.bind_all("<Control-Shift-Z>", lambda e: self.redo())
        self.root.bind_all("<Control-y>", lambda e: self.redo())
        self.root.bind_all("<Control-c>", lambda e: self.copy())
        self.root.bind_all("<Control-x>", lambda e: self.cut())
        self.root.bind_all("<Control-v>", lambda e: self.paste())
        self.root.bind_all("<Delete>", lambda e: self.clear())

    # ---------- display & zoom ----------
    def _slider_zoom(self, val):
        try:
            z = int(val) / 100.0
        except Exception:
            return
        self.zoom_level = max(0.1, min(10.0, z))
        self._update_zoom_label()
        self._display_image(center=False)

    def zoom_in(self):
        self.zoom_level = min(self.zoom_level * 1.25, 10.0)
        self.zoom_var.set(int(self.zoom_level * 100))
        self._update_zoom_label()
        self._display_image(center=False)

    def zoom_out(self):
        self.zoom_level = max(self.zoom_level / 1.25, 0.1)
        self.zoom_var.set(int(self.zoom_level * 100))
        self._update_zoom_label()
        self._display_image(center=False)

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.zoom_var.set(100)
        self._update_zoom_label()
        self._display_image(center=True)

    def _update_zoom_label(self):
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def _mouse_wheel(self, event):
        delta = 0
        if hasattr(event, "delta"):
            delta = event.delta
        elif hasattr(event, "num") and event.num in (4, 5):
            delta = 120 if event.num == 4 else -120
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def _get_display_image(self):
        if not self.original_image:
            return None
        w, h = self.original_image.size
        new_w = max(1, int(round(w * self.zoom_level)))
        new_h = max(1, int(round(h * self.zoom_level)))
        return self.original_image.resize((new_w, new_h), Image.LANCZOS)

    def _display_image(self, center=False):
        self.canvas.delete("all")
        if not self.original_image:
            self.show_home()
            self._update_size_fields()
            return
        disp = self._get_display_image()
        self._tkimg = ImageTk.PhotoImage(disp)
        canvas_w = self.canvas.winfo_width() or self.canvas.winfo_reqwidth()
        canvas_h = self.canvas.winfo_height() or self.canvas.winfo_reqheight()
        img_w, img_h = disp.size
        if center or (img_w < canvas_w and img_h < canvas_h):
            x = max(0, (canvas_w - img_w) // 2)
            y = max(0, (canvas_h - img_h) // 2)
        else:
            x = 0
            y = 0
        self._last_img_origin_x = x
        self._last_img_origin_y = y
        self.canvas.create_image(x, y, anchor=tk.NW, image=self._tkimg)
        self.canvas.config(scrollregion=(0, 0, x + img_w, y + img_h))
        self.hide_home()
        self._update_size_fields()

    # ---------- file ops ----------
    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tiff *.bmp")])
        if not path:
            return
        try:
            opened = Image.open(path)
        except Exception as e:
            messagebox.showerror("Open Error", f"Could not open image:\n{e}")
            return
        self.original_image = opened.convert("RGBA") if opened.mode in ("RGBA", "LA") else opened.convert("RGB")
        self.history.reset()
        self.history.push(self.original_image)
        self.zoom_level = 1.0
        self.zoom_var.set(100)
        self._update_zoom_label()
        self._display_image(center=True)
        self.filename_label.config(text=f"File: {os.path.basename(path)}")
        self.hide_home()
        self._update_size_fields()

    def save_as(self):
        if not self.original_image:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not path:
            return
        self.original_image.convert("RGB").save(path)

    def export_image(self):
        if not self.original_image:
            return
        path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if not path:
            return
        self.original_image.convert("RGB").save(path)

    def show_file_info(self):
        if not self.original_image:
            messagebox.showinfo("File Info", "No image loaded.")
            return
        w, h = self.original_image.size
        messagebox.showinfo("File Info", f"Size: {w} x {h} pixels")

    # ---------- edits ----------
    def apply_and_push(self, fn):
        if not self.original_image:
            return
        try:
            self.history.push(self.original_image)
            self.original_image = fn(self.original_image)
            self._display_image(center=True)
        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not apply edit:\n{e}")

    def invert(self):
        self.apply_and_push(ImageTools.invert)

    def black_and_white(self):
        self.apply_and_push(ImageTools.to_grayscale)

    def transform(self, action):
        if action == "ccw":
            self.apply_and_push(lambda im: ImageTools.rotate(im, 90))
        elif action == "cw":
            self.apply_and_push(lambda im: ImageTools.rotate(im, -90))
        elif action == "180":
            self.apply_and_push(lambda im: ImageTools.rotate(im, 180))
        elif action == "flip_h":
            self.apply_and_push(ImageTools.flip_horizontal)
        elif action == "flip_v":
            self.apply_and_push(ImageTools.flip_vertical)

    # ---------- Brightness/Contrast dialog ----------
    def adjust_brightness_contrast(self):
        if not self.original_image:
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Brightness & Contrast")
        dlg.transient(self.root)
        dlg.grab_set()
        tk.Label(dlg, text="Brightness").pack(padx=8, pady=(8,0))
        b_var = tk.DoubleVar(value=1.0)
        b_slider = tk.Scale(dlg, from_=0.1, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=b_var, length=300)
        b_slider.pack(padx=8, pady=4)
        tk.Label(dlg, text="Contrast").pack(padx=8, pady=(8,0))
        c_var = tk.DoubleVar(value=1.0)
        c_slider = tk.Scale(dlg, from_=0.1, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=c_var, length=300)
        c_slider.pack(padx=8, pady=4)

        def preview():
            temp = ImageEnhance.Brightness(self.original_image).enhance(b_var.get())
            temp = ImageEnhance.Contrast(temp).enhance(c_var.get())
            self._tk_preview = ImageTk.PhotoImage(temp.resize((int(temp.width * self.zoom_level), int(temp.height * self.zoom_level)), Image.LANCZOS))
            self.canvas.delete("all")
            self.canvas.create_image(self._last_img_origin_x, self._last_img_origin_y, anchor=tk.NW, image=self._tk_preview)
            self.canvas.config(scrollregion=(0, 0, self._tk_preview.width(), self._tk_preview.height()))

        def apply_changes():
            self.apply_and_push(lambda im: ImageEnhance.Brightness(im).enhance(b_var.get()).convert("RGB"))
            self.apply_and_push(lambda im: ImageEnhance.Contrast(im).enhance(c_var.get()).convert("RGB"))
            dlg.destroy()

        preview_btn = tk.Button(dlg, text="Preview", command=preview)
        preview_btn.pack(side=tk.LEFT, padx=8, pady=8)
        apply_btn = tk.Button(dlg, text="Apply", command=apply_changes)
        apply_btn.pack(side=tk.RIGHT, padx=8, pady=8)

    # ---------- Photo filter dialog ----------
    def photo_filter_dialog(self):
        if not self.original_image:
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Photo Filter Density")
        dlg.transient(self.root)
        dlg.grab_set()
        tk.Label(dlg, text="Density (0.0 - 1.0)").pack(padx=8, pady=(8,0))
        d_var = tk.DoubleVar(value=0.2)
        d_slider = tk.Scale(dlg, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, variable=d_var, length=300)
        d_slider.pack(padx=8, pady=8)

        def apply_filter():
            self.apply_and_push(lambda im: ImageTools.photo_filter(im, density=d_var.get()))
            dlg.destroy()

        tk.Button(dlg, text="Apply", command=apply_filter).pack(pady=(0,8), padx=8)

    # ---------- copy/cut/paste/clear ----------
    def copy(self):
        if self.original_image:
            self.clipboard_image = self.original_image.copy()
            self.color_label.config(text="Color: Copied")
        else:
            self.color_label.config(text="Color: -")

    def paste(self):
        if self.clipboard_image:
            self.history.push(self.original_image)
            self.original_image = self.clipboard_image.copy()
            self._display_image(center=True)
            self.filename_label.config(text="File: (pasted)")
        else:
            messagebox.showinfo("Paste", "Clipboard is empty.")

    def cut(self):
        if self.original_image:
            self.copy()
            self.clear()

    def clear(self):
        if self.original_image:
            self.history.push(self.original_image)
        self.original_image = None
        self.canvas.delete("all")
        self.filename_label.config(text="File: None")
        self.color_label.config(text="Color: -")
        self.zoom_var.set(100)
        self.zoom_label.config(text="100%")
        self.show_home()

    # ---------- undo/redo ----------
    def undo(self):
        if self.history.can_undo():
            img = self.history.undo()
            self.original_image = img.copy() if img else None
            self._display_image(center=True)

    def redo(self):
        if self.history.can_redo():
            img = self.history.redo()
            self.original_image = img.copy() if img else None
            self._display_image(center=True)

    # ---------- home screen ----------
    def show_home(self):
        self.canvas.delete("all")
        self.home_frame.place(relx=0.5, rely=0.5, anchor="center")

    def hide_home(self):
        self.home_frame.place_forget()

    # ---------- tools (move, zoom, eyedropper) ----------
    def set_tool(self, tool_name):
        # unbind tool-specific actions
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.active_tool = tool_name
        self.color_label.config(text=f"Tool: {tool_name}")
        if tool_name == "move":
            self.canvas.bind("<Button-1>", self._move_start)
            self.canvas.bind("<B1-Motion>", self._move_drag)
        elif tool_name == "eyedropper":
            self.canvas.bind("<Button-1>", self._eyedrop_pick)
        elif tool_name == "zoom":
            self.canvas.bind("<Button-1>", self._zoom_click)
        elif tool_name == "brush":
            self.canvas.bind("<Button-1>", self._brush_start)
            self.canvas.bind("<B1-Motion>", self._brush_draw)
            self.canvas.bind("<ButtonRelease-1>", self._brush_end)
        elif tool_name == "eraser":
            self.canvas.bind("<Button-1>", self._eraser_start)
            self.canvas.bind("<B1-Motion>", self._eraser_draw)
            self.canvas.bind("<ButtonRelease-1>", self._eraser_end)

    # --- Brush tool (simple black line) ---
    def _brush_start(self, event):
        if not self.original_image:
            return
        self._drawing = True
        self._brush_last = (event.x, event.y)
        self._brush_draw(event)

    def _brush_draw(self, event):
        if not self.original_image or not getattr(self, '_drawing', False):
            return
        x0, y0 = self._brush_last
        x1, y1 = event.x, event.y
        img_x0 = int((self.canvas.canvasx(x0) - self._last_img_origin_x) / self.zoom_level)
        img_y0 = int((self.canvas.canvasy(y0) - self._last_img_origin_y) / self.zoom_level)
        img_x1 = int((self.canvas.canvasx(x1) - self._last_img_origin_x) / self.zoom_level)
        img_y1 = int((self.canvas.canvasy(y1) - self._last_img_origin_y) / self.zoom_level)
        from PIL import ImageDraw
        im = self.original_image.copy()
        draw = ImageDraw.Draw(im)
        draw.line([img_x0, img_y0, img_x1, img_y1], fill="black", width=8)
        self.original_image = im
        self._brush_last = (x1, y1)
        self._display_image(center=False)

    def _brush_end(self, event):
        if not self.original_image:
            return
        self._drawing = False
        self.history.push(self.original_image)

    # --- Eraser tool (clear to transparency) ---
    def _eraser_start(self, event):
        if not self.original_image:
            return
        self._drawing = True
        self._eraser_last = (event.x, event.y)
        self._eraser_draw(event)

    def _eraser_draw(self, event):
        if not self.original_image or not getattr(self, '_drawing', False):
            return
        x0, y0 = self._eraser_last
        x1, y1 = event.x, event.y
        img_x0 = int((self.canvas.canvasx(x0) - self._last_img_origin_x) / self.zoom_level)
        img_y0 = int((self.canvas.canvasy(y0) - self._last_img_origin_y) / self.zoom_level)
        img_x1 = int((self.canvas.canvasx(x1) - self._last_img_origin_x) / self.zoom_level)
        img_y1 = int((self.canvas.canvasy(y1) - self._last_img_origin_y) / self.zoom_level)
        from PIL import ImageDraw
        im = self.original_image.convert("RGBA").copy()
        draw = ImageDraw.Draw(im)
        draw.line([img_x0, img_y0, img_x1, img_y1], fill=(0,0,0,0), width=16)
        self.original_image = im
        self._eraser_last = (x1, y1)
        self._display_image(center=False)

    def _eraser_end(self, event):
        if not self.original_image:
            return
        self._drawing = False
        self.history.push(self.original_image)

    def _move_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _move_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _zoom_click(self, event):
        if not self.original_image:
            return
        self._zoom_at(event.x, event.y, 1.25)

    def _eyedrop_pick(self, event):
        if not self.original_image:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = int((canvas_x - self._last_img_origin_x) / self.zoom_level)
        img_y = int((canvas_y - self._last_img_origin_y) / self.zoom_level)
        if img_x < 0 or img_y < 0 or img_x >= self.original_image.width or img_y >= self.original_image.height:
            return
        rgb = self.original_image.convert("RGB").getpixel((img_x, img_y))
        hexc = ColorUtils.rgb_to_hex(rgb)
        cmyk = ColorUtils.rgb_to_cmyk(*rgb)
        hsv, hsl = ColorUtils.rgb_to_hsv_hsl(*rgb)  # <-- new additions
        # marker
        r = 6
        try:
            if self.marker_id:
                self.canvas.delete(self.marker_id)
        except Exception:
            pass
        self.marker_id = self.canvas.create_oval(canvas_x - r, canvas_y - r, canvas_x + r, canvas_y + r, outline="#000000", width=2, fill=hexc)
        # show swatch with HSV and HSL included
        self._show_color_swatch(event.x_root, event.y_root, rgb, hexc, cmyk, hsv, hsl)
        self.color_label.config(text=f"Color: {hexc}  RGB:{rgb}")

    def _show_color_swatch(self, root_x, root_y, rgb, hexc, cmyk, hsv, hsl):
        if self.swatch_window:
            try:
                self.swatch_window.destroy()
            except Exception:
                pass
            self.swatch_window = None
        sw = tk.Toplevel(self.root)
        sw.wm_overrideredirect(True)
        sw.geometry(f"+{root_x + 16}+{root_y + 8}")
        sw.config(bg="#222", padx=6, pady=6)
        block = tk.Frame(sw, width=44, height=44, bg=hexc, relief=tk.SUNKEN, bd=1)
        block.pack(side=tk.LEFT, padx=(0,8))
        txt = f"{hexc}\nRGB: {rgb}\nCMYK: {cmyk}\nHSV: {hsv}\nHSL: {hsl}"
        lbl = tk.Label(sw, text=txt, bg="#222", fg="white", justify=tk.LEFT, font=("Arial", 9))
        lbl.pack(side=tk.LEFT)
        self.swatch_window = sw
        # auto-destroy after 1.8s
        sw.after(1800, lambda: (sw.destroy(), setattr(self, 'swatch_window', None)))

    def _zoom_at(self, canvas_x, canvas_y, factor):
        # convert canvas coords -> image coords then update zoom and try to keep point centered
        img_x = (self.canvas.canvasx(canvas_x) - self._last_img_origin_x) / self.zoom_level
        img_y = (self.canvas.canvasy(canvas_y) - self._last_img_origin_y) / self.zoom_level
        self.zoom_level = max(0.1, min(10.0, self.zoom_level * factor))
        self.zoom_var.set(int(self.zoom_level * 100))
        self._update_zoom_label()
        self._display_image(center=False)
        # adjust view so clicked point stays near the same location
        new_canvas_x = img_x * self.zoom_level + self._last_img_origin_x
        new_canvas_y = img_y * self.zoom_level + self._last_img_origin_y
        dx = new_canvas_x - canvas_x
        dy = new_canvas_y - canvas_y
        try:
            self.canvas.xview_scroll(int(dx), "units")
            self.canvas.yview_scroll(int(dy), "units")
        except Exception:
            pass

# ---------------- run ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.mainloop()
