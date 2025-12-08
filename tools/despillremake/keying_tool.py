import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageTk, ImageColor
import math
import sys
import threading

# ==========================================
# CORE IMAGE PROCESSING LOGIC (Pure Python)
# ==========================================

# --- Math Constants ---
Xn, Yn, Zn = 95.0489, 100.0, 108.8840
DELTA = 0.20689655172
DELTA_3 = DELTA ** 3
DELTA_2 = DELTA ** 2

# --- Helper Functions ---

def linearize_srgb(v):
    if v <= 0.04045: return v / 12.92
    return ((v + 0.055) / 1.055) ** 2.4

def func_lab(t):
    if t > DELTA_3: return t ** (1.0 / 3.0)
    return (t / (3.0 * DELTA_2)) + (4.0 / 29.0)

def rgb_to_lab(r, g, b):
    # 1. Linearize
    lin_r = linearize_srgb(r)
    lin_g = linearize_srgb(g)
    lin_b = linearize_srgb(b)
    
    # 2. XYZ
    x = (lin_r * 0.4124 + lin_g * 0.3576 + lin_b * 0.1805) * 100.0
    y = (lin_r * 0.2126 + lin_g * 0.7152 + lin_b * 0.0722) * 100.0
    z = (lin_r * 0.0193 + lin_g * 0.1192 + lin_b * 0.9505) * 100.0
    
    # 3. Lab
    l_val = 116.0 * func_lab(y / Yn) - 16.0
    a_val = 500.0 * (func_lab(x / Xn) - func_lab(y / Yn))
    b_val = 200.0 * (func_lab(y / Yn) - func_lab(z / Zn))
    return l_val, a_val, b_val

def clamp(val, min_v=0, max_v=255):
    return max(min_v, min(max_v, int(val)))

# --- Processing Engines ---

def run_despill(img, key_color, method, preserve_luma):
    width, height = img.size
    pixels = img.load()
    new_img = Image.new("RGBA", (width, height))
    new_pixels = new_img.load()
    
    luma_r, luma_g, luma_b = 0.2126, 0.7152, 0.0722

    for x in range(width):
        for y in range(height):
            r_int, g_int, b_int, a_int = pixels[x, y]
            r, g, b = r_int/255.0, g_int/255.0, b_int/255.0
            
            orig_r, orig_g, orig_b = r, g, b
            limit = 0.0

            if key_color == 'Green':
                if method == 'Average': limit = (r + b) / 2.0
                elif method == 'Double Red': limit = (2.0 * r + b) / 3.0
                elif method == 'Double Average': limit = (2.0 * b + r) / 3.0
                elif method == 'Limit': limit = b
                if g > limit: g = limit
            else: # Blue
                if method == 'Average': limit = (r + g) / 2.0
                elif method == 'Double Red': limit = (2.0 * r + g) / 3.0
                elif method == 'Double Average': limit = (2.0 * g + r) / 3.0
                elif method == 'Limit': limit = g
                if b > limit: b = limit

            if preserve_luma:
                diff_r, diff_g, diff_b = orig_r - r, orig_g - g, orig_b - b
                luma = (abs(diff_r)*luma_r) + (abs(diff_g)*luma_g) + (abs(diff_b)*luma_b)
                r += luma; g += luma; b += luma

            new_pixels[x, y] = (clamp(r*255), clamp(g*255), clamp(b*255), a_int)
    
    return new_img

def run_chromakey(img, hex_color, lower, upper, shadows, highlights, invert, mask_only):
    width, height = img.size
    pixels = img.load()
    new_img = Image.new("RGBA", (width, height))
    new_pixels = new_img.load()

    # Pre-calc key Lab
    k_rgb = ImageColor.getrgb(hex_color)
    key_lab = rgb_to_lab(k_rgb[0]/255.0, k_rgb[1]/255.0, k_rgb[2]/255.0)

    for x in range(width):
        for y in range(height):
            r_int, g_int, b_int, a_int = pixels[x, y]
            r, g, b = r_int/255.0, g_int/255.0, b_int/255.0
            
            # Un-multiply alpha
            if a_int > 0:
                alpha_f = a_int / 255.0
                pix_lab = rgb_to_lab(r/alpha_f, g/alpha_f, b/alpha_f)
            else:
                pix_lab = rgb_to_lab(r, g, b)

            # Distance
            diff_L = key_lab[0] - pix_lab[0]
            diff_a = key_lab[1] - pix_lab[1]
            diff_b = key_lab[2] - pix_lab[2]
            dist = math.sqrt(diff_L**2 + diff_a**2 + diff_b**2)

            # Mask
            mask = 1.0
            if dist < lower: mask = 0.0
            elif dist < upper: mask = (dist - lower) / (upper - lower)
            
            # Shadows/Highlights
            mask = shadows * 0.01 * (highlights * 0.01 * mask - 1.0) + 1.0
            mask = max(0.0, min(1.0, mask))

            if invert: mask = 1.0 - mask

            if mask_only:
                val = int(mask * 255)
                new_pixels[x, y] = (val, val, val, 255)
            else:
                new_a = int(a_int * mask)
                new_pixels[x, y] = (r_int, g_int, b_int, new_a)

    return new_img

# ==========================================
# GUI APPLICATION
# ==========================================

class KeyingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Keying Suite (Olive Engine)")
        self.root.geometry("1000x700")

        # State
        self.original_image = None # Full Res
        self.preview_image = None  # Small Res for UI
        self.processed_preview = None
        self.current_mode = "Despill" # or "Chroma"
        self.key_color_hex = "#00FF00"
        
        # Layout
        self.setup_ui()

    def setup_ui(self):
        # Top Bar
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)
        tk.Button(top_frame, text="Open Image", command=self.load_image).pack(side=tk.LEFT, padx=10)
        tk.Button(top_frame, text="Save Result", command=self.save_image, bg="#dddddd").pack(side=tk.LEFT, padx=10)
        
        # Main Content
        content = tk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True)

        # Left Control Panel
        controls = tk.Frame(content, width=300, padx=10, pady=10, relief=tk.RIDGE, borderwidth=2)
        controls.pack(side=tk.LEFT, fill=tk.Y)

        # Notebook for Tools
        self.notebook = ttk.Notebook(controls)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # --- Despill Tab ---
        self.tab_despill = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_despill, text='Despill')
        
        ttk.Label(self.tab_despill, text="Key Color:").pack(anchor=tk.W, pady=(10,0))
        self.var_ds_color = tk.StringVar(value="Green")
        ttk.Radiobutton(self.tab_despill, text="Green", variable=self.var_ds_color, value="Green", command=self.trigger_update).pack(anchor=tk.W)
        ttk.Radiobutton(self.tab_despill, text="Blue", variable=self.var_ds_color, value="Blue", command=self.trigger_update).pack(anchor=tk.W)

        ttk.Label(self.tab_despill, text="Method:").pack(anchor=tk.W, pady=(10,0))
        self.var_ds_method = tk.StringVar(value="Average")
        methods = ["Average", "Double Red", "Double Average", "Limit"]
        ds_menu = ttk.OptionMenu(self.tab_despill, self.var_ds_method, "Average", *methods, command=lambda _: self.trigger_update())
        ds_menu.pack(fill=tk.X)

        self.var_ds_luma = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.tab_despill, text="Preserve Luminance", variable=self.var_ds_luma, command=self.trigger_update).pack(anchor=tk.W, pady=10)

        # --- Chroma Key Tab ---
        self.tab_chroma = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_chroma, text='Chroma Key')

        # Color Picker
        color_frame = tk.Frame(self.tab_chroma, pady=10)
        color_frame.pack(fill=tk.X)
        self.btn_color = tk.Button(color_frame, text="Pick Key Color", bg=self.key_color_hex, command=self.pick_color)
        self.btn_color.pack(fill=tk.X)

        # Sliders helper
        def make_slider(parent, label, min_v, max_v, default, var):
            ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(10,0))
            s = ttk.Scale(parent, from_=min_v, to=max_v, variable=var, command=lambda v: self.trigger_update())
            s.pack(fill=tk.X)
            return s

        self.var_ck_lower = tk.DoubleVar(value=5.0)
        make_slider(self.tab_chroma, "Lower Tolerance", 0, 100, 5.0, self.var_ck_lower)

        self.var_ck_upper = tk.DoubleVar(value=25.0)
        make_slider(self.tab_chroma, "Upper Tolerance", 0, 100, 25.0, self.var_ck_upper)

        self.var_ck_high = tk.DoubleVar(value=100.0)
        make_slider(self.tab_chroma, "Highlights", 0, 200, 100.0, self.var_ck_high)

        self.var_ck_shadow = tk.DoubleVar(value=100.0)
        make_slider(self.tab_chroma, "Shadows", 0, 200, 100.0, self.var_ck_shadow)

        self.var_ck_invert = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.tab_chroma, text="Invert Mask", variable=self.var_ck_invert, command=self.trigger_update).pack(anchor=tk.W, pady=5)

        self.var_ck_maskonly = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.tab_chroma, text="Show Mask Only", variable=self.var_ck_maskonly, command=self.trigger_update).pack(anchor=tk.W, pady=5)

        # Right Image Panel
        self.canvas_frame = tk.Frame(content, bg="#333333")
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#333333", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Status
        self.status_var = tk.StringVar(value="Ready. Load an image to begin.")
        tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    # --- Logic ---

    def pick_color(self):
        color = colorchooser.askcolor(color=self.key_color_hex, title="Select Key Color")
        if color[1]:
            self.key_color_hex = color[1]
            self.btn_color.configure(bg=self.key_color_hex)
            self.trigger_update()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path: return

        try:
            self.original_image = Image.open(path).convert("RGBA")
            
            # Create a small preview image (Max 500px) for performance
            self.preview_image = self.original_image.copy()
            self.preview_image.thumbnail((500, 500))
            
            self.status_var.set(f"Loaded {path}")
            self.trigger_update()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")

    def on_tab_change(self, event):
        tab_id = self.notebook.index(self.notebook.select())
        self.current_mode = "Despill" if tab_id == 0 else "Chroma"
        self.trigger_update()

    def trigger_update(self):
        if not self.preview_image: return
        
        # Debounce or simple thread to prevent UI freeze
        # Since this is pure python and might take 0.2-0.5s for preview, we run it
        # and then update UI
        self.status_var.set("Processing preview...")
        self.root.update_idletasks() # Force UI refresh
        
        # Gather params
        params = self.get_params()
        
        # Run processing directly (threading is better but adds complexity to sync)
        # Given the "thumbnail" approach, this should be tolerable.
        res_img = self.process_image(self.preview_image.copy(), params)
        
        # Update Canvas
        self.display_image(res_img)
        self.status_var.set("Preview Updated.")

    def get_params(self):
        return {
            'mode': self.current_mode,
            'ds_color': self.var_ds_color.get(),
            'ds_method': self.var_ds_method.get(),
            'ds_luma': self.var_ds_luma.get(),
            'ck_color': self.key_color_hex,
            'ck_low': self.var_ck_lower.get(),
            'ck_high': self.var_ck_upper.get(),
            'ck_shadow': self.var_ck_shadow.get(),
            'ck_highlight': self.var_ck_high.get(),
            'ck_invert': self.var_ck_invert.get(),
            'ck_maskonly': self.var_ck_maskonly.get()
        }

    def process_image(self, img_obj, params):
        if params['mode'] == 'Despill':
            return run_despill(img_obj, params['ds_color'], params['ds_method'], params['ds_luma'])
        else:
            return run_chromakey(
                img_obj, params['ck_color'], 
                params['ck_low'], params['ck_high'], 
                params['ck_shadow'], params['ck_highlight'], 
                params['ck_invert'], params['ck_maskonly']
            )

    def display_image(self, img):
        self.tk_img = ImageTk.PhotoImage(img)
        
        # Center image in canvas
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = img.size
        
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self.tk_img)

    def save_image(self):
        if not self.original_image: return
        
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path: return

        self.status_var.set("Processing Full Resolution... This may take a while.")
        self.root.update()

        try:
            params = self.get_params()
            # Process the original FULL SIZE image
            final_img = self.process_image(self.original_image.copy(), params)
            final_img.save(path)
            messagebox.showinfo("Success", f"Saved to {path}")
            self.status_var.set("Saved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error saving.")

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyingApp(root)
    root.mainloop()