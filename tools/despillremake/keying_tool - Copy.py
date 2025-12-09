import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageTk, ImageColor, ImageDraw, ImageChops
import math
import threading

# ==========================================
# PART 1: OPTIMIZED MATH & LUTS
# ==========================================

Xn, Yn, Zn = 95.0489, 100.0, 108.8840
DELTA = 0.20689655172
DELTA_3 = DELTA ** 3
DELTA_2 = DELTA ** 2

def _calc_linear_srgb(v_int):
    v = v_int / 255.0
    if v <= 0.04045: return v / 12.92
    return ((v + 0.055) / 1.055) ** 2.4

LINEAR_LUT = [_calc_linear_srgb(i) for i in range(256)]

def func_lab(t):
    if t > DELTA_3: return t ** (1.0 / 3.0)
    return (t / (3.0 * DELTA_2)) + (4.0 / 29.0)

def rgb_to_lab_fast(r_int, g_int, b_int):
    lin_r = LINEAR_LUT[r_int]
    lin_g = LINEAR_LUT[g_int]
    lin_b = LINEAR_LUT[b_int]
    x = (lin_r * 0.4124 + lin_g * 0.3576 + lin_b * 0.1805) * 100.0
    y = (lin_r * 0.2126 + lin_g * 0.7152 + lin_b * 0.0722) * 100.0
    z = (lin_r * 0.0193 + lin_g * 0.1192 + lin_b * 0.9505) * 100.0
    l_val = 116.0 * func_lab(y / Yn) - 16.0
    a_val = 500.0 * (func_lab(x / Xn) - func_lab(y / Yn))
    b_val = 200.0 * (func_lab(y / Yn) - func_lab(z / Zn))
    return l_val, a_val, b_val

def hex_to_lab(hex_color):
    k_rgb = ImageColor.getrgb(hex_color)
    return rgb_to_lab_fast(k_rgb[0], k_rgb[1], k_rgb[2])

# ==========================================
# PART 2: PROCESSING ENGINES
# ==========================================

def run_despill(img, key_color, method, preserve_luma, app_ref=None, job_id=None):
    width, height = img.size
    pixels = img.load()
    new_img = Image.new("RGBA", (width, height))
    new_pixels = new_img.load()
    
    luma_r, luma_g, luma_b = 0.2126, 0.7152, 0.0722
    
    m_idx = 0
    if method == 'Double Red': m_idx = 1
    elif method == 'Double Average': m_idx = 2
    elif method == 'Limit': m_idx = 3
    
    is_green = (key_color == 'Green')

    for x in range(width):
        if app_ref and app_ref.current_job_id != job_id: return None
        for y in range(height):
            r_int, g_int, b_int, a_int = pixels[x, y]
            r, g, b = r_int/255.0, g_int/255.0, b_int/255.0
            orig_r, orig_g, orig_b = r, g, b
            limit = 0.0

            if is_green:
                if m_idx == 0: limit = (r + b) * 0.5
                elif m_idx == 1: limit = (2.0 * r + b) * 0.33333
                elif m_idx == 2: limit = (2.0 * b + r) * 0.33333
                elif m_idx == 3: limit = b
                if g > limit: g = limit
            else: 
                if m_idx == 0: limit = (r + g) * 0.5
                elif m_idx == 1: limit = (2.0 * r + g) * 0.33333
                elif m_idx == 2: limit = (2.0 * g + r) * 0.33333
                elif m_idx == 3: limit = g
                if b > limit: b = limit

            if preserve_luma:
                diff_r, diff_g, diff_b = orig_r - r, orig_g - g, orig_b - b
                luma = (abs(diff_r)*luma_r) + (abs(diff_g)*luma_g) + (abs(diff_b)*luma_b)
                r += luma; g += luma; b += luma

            nr = int(r * 255)
            ng = int(g * 255)
            nb = int(b * 255)
            new_pixels[x, y] = (
                255 if nr > 255 else (0 if nr < 0 else nr),
                255 if ng > 255 else (0 if ng < 0 else ng),
                255 if nb > 255 else (0 if nb < 0 else nb),
                a_int
            )
    return new_img

def run_chromakey(img, key_lab, lower, upper, shadows, highlights, invert, mask_only, app_ref=None, job_id=None):
    width, height = img.size
    pixels = img.load()
    new_img = Image.new("RGBA", (width, height))
    new_pixels = new_img.load()

    key_L, key_a, key_b = key_lab
    shad_factor = shadows * 0.01
    high_factor = highlights * 0.01

    for x in range(width):
        if app_ref and app_ref.current_job_id != job_id: return None
        for y in range(height):
            r_int, g_int, b_int, a_int = pixels[x, y]
            
            if a_int > 0 and a_int < 255:
                alpha_f = 255.0 / a_int
                pix_lab = rgb_to_lab_fast(
                    int(r_int * alpha_f) if r_int * alpha_f <= 255 else 255, 
                    int(g_int * alpha_f) if g_int * alpha_f <= 255 else 255, 
                    int(b_int * alpha_f) if b_int * alpha_f <= 255 else 255
                )
            else:
                pix_lab = rgb_to_lab_fast(r_int, g_int, b_int)

            diff_L = key_L - pix_lab[0]
            diff_a = key_a - pix_lab[1]
            diff_b = key_b - pix_lab[2]
            dist = math.sqrt(diff_L*diff_L + diff_a*diff_a + diff_b*diff_b)

            mask = 1.0
            if dist < lower: mask = 0.0
            elif dist < upper: mask = (dist - lower) / (upper - lower)
            
            mask = shad_factor * (high_factor * mask - 1.0) + 1.0
            if mask < 0.0: mask = 0.0
            elif mask > 1.0: mask = 1.0

            if invert: mask = 1.0 - mask

            if mask_only:
                val = int(mask * 255)
                new_pixels[x, y] = (val, val, val, 255)
            else:
                new_a = int(a_int * mask)
                new_pixels[x, y] = (r_int, g_int, b_int, new_a)
    return new_img

def run_alpha_extract(img, key_color_hex, bg_brightness, edge_softness, app_ref=None, job_id=None):
    """
    Extract alpha from green/blue screen by analyzing how much the key channel is darkened.
    Semi-transparent elements (shadows, smoke) darken the green proportionally to their opacity.
    
    Algorithm:
    - For green screen: alpha = 1.0 - (green_value / expected_green)
    - expected_green = bg_brightness (the brightness of pure green screen areas)
    - Foreground RGB is estimated by removing the green screen contribution
    """
    width, height = img.size
    pixels = img.load()
    new_img = Image.new("RGBA", (width, height))
    new_pixels = new_img.load()
    
    # Parse key color to determine which channel to use
    k_rgb = ImageColor.getrgb(key_color_hex)
    # Determine if green or blue screen based on which channel is dominant
    is_green = k_rgb[1] >= k_rgb[2]
    
    # bg_brightness is the expected value of the key channel in pure BG areas (0-255)
    bg_val = bg_brightness / 255.0
    if bg_val < 0.01:
        bg_val = 0.01  # Prevent division by zero
    
    edge_factor = edge_softness / 100.0  # 0.0 = hard edge, 1.0 = soft edge
    
    for x in range(width):
        if app_ref and app_ref.current_job_id != job_id:
            return None
        for y in range(height):
            r_int, g_int, b_int, a_int = pixels[x, y]
            r, g, b = r_int / 255.0, g_int / 255.0, b_int / 255.0
            
            # Get the key channel value
            if is_green:
                key_channel = g
                other1, other2 = r, b
            else:
                key_channel = b
                other1, other2 = r, g
            
            # Calculate alpha based on how much the key channel differs from expected
            # A pure green pixel (0, 255, 0) on green screen has alpha = 0
            # A 50% shadow (0, 127, 0) has alpha ≈ 0.5
            # A solid object with low green has alpha = 1.0
            
            # FIXED: Only apply alpha extraction if green is DOMINANT (higher than both R and B)
            # This prevents treating natural colors (skin, red objects) as green screen
            max_other = max(other1, other2)
            
            # Pixel is "green screen" if green is higher than both R and B
            if key_channel > max_other + 0.05 and key_channel > 0.1:
                # This is likely BG or semi-transparent overlay on green
                # Alpha = 1 - (key_channel / bg_brightness)
                raw_alpha = 1.0 - (key_channel / bg_val)
                
                # Apply edge softness
                if edge_factor > 0 and raw_alpha > 0 and raw_alpha < 1:
                    raw_alpha = raw_alpha ** (1.0 / (1.0 + edge_factor))
                
                # Clamp alpha
                if raw_alpha < 0:
                    raw_alpha = 0.0
                elif raw_alpha > 1:
                    raw_alpha = 1.0
                
                # Estimate foreground color - FIXED: don't divide R/B by alpha
                if raw_alpha > 0.01:
                    bg_contribution = (1.0 - raw_alpha) * bg_val
                    if is_green:
                        fg_g = max(0, min(1, (g - bg_contribution) / raw_alpha)) if raw_alpha > 0 else 0
                        fg_r = r  # Keep R as-is
                        fg_b = b  # Keep B as-is
                    else:
                        fg_b = max(0, min(1, (b - bg_contribution) / raw_alpha)) if raw_alpha > 0 else 0
                        fg_r = r
                        fg_g = g
                else:
                    fg_r, fg_g, fg_b = 0, 0, 0
                
                final_alpha = int(raw_alpha * (a_int / 255.0) * 255)
                
                new_pixels[x, y] = (
                    int(fg_r * 255),
                    int(fg_g * 255),
                    int(fg_b * 255),
                    final_alpha
                )
            else:
                # Non-green-dominant pixel = solid foreground, keep as-is
                new_pixels[x, y] = (r_int, g_int, b_int, a_int)
    
    return new_img

# ==========================================
# PART 3: GUI APPLICATION
# ==========================================

class KeyingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Keying Tool v14 (Alpha Extract)")

        self.root.geometry("1100x900")

        self.ui_ready = False 
        self.picking_mode = False
        self.erasing_mode = False
        
        self.current_job_id = 0     
        self.pending_params = None  
        self.is_processing = False  

        self.original_image = None
        self.manual_mask = None     
        self.preview_image = None   
        self.preview_mask = None    
        self.processed_preview = None 
        
        self.zoom_scale = 1.0
        self.canvas_image_id = None 
        
        self.current_mode = "Chroma" 
        self.key_color_hex = "#00FF00"
        
        # New: View Mode (checker, black, white, alpha)
        self.view_mode = "Checker"

        self.setup_ui()

    def setup_ui(self):
        # Toolbar
        top_frame = tk.Frame(self.root, pady=10, bg="#e0e0e0")
        top_frame.pack(fill=tk.X)
        
        btn_opts = {'padx': 15, 'pady': 5}
        tk.Button(top_frame, text="📂 Open Image", command=self.load_image, bg="white", **btn_opts).pack(side=tk.LEFT, padx=10)
        self.btn_save = tk.Button(top_frame, text="💾 Save PNG", command=self.save_image, bg="#d0f0c0", **btn_opts)
        self.btn_save.pack(side=tk.LEFT, padx=10)
        tk.Button(top_frame, text="✂ Crop to Content", command=self.auto_crop, bg="#ffd0d0", **btn_opts).pack(side=tk.LEFT, padx=10)
        
        content = tk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        controls = tk.Frame(content, width=320, padx=15, pady=15, relief=tk.RIDGE, borderwidth=1)
        controls.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(controls, text="Settings", font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

        self.notebook = ttk.Notebook(controls)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.tab_chroma = ttk.Frame(self.notebook)
        self.tab_despill = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_chroma, text='Chroma Key')
        frm_ck = tk.Frame(self.tab_chroma, pady=10)
        frm_ck.pack(fill=tk.X)

        self.var_apply_chroma = tk.BooleanVar(value=True)
        chk_active = tk.Checkbutton(frm_ck, text="Enable Chroma Key", variable=self.var_apply_chroma, command=self.trigger_update, font=("Arial", 11, "bold"), fg="blue")
        chk_active.pack(anchor=tk.W, pady=(0, 10))

        lbl_col = ttk.Label(frm_ck, text="Tools:")
        lbl_col.pack(anchor=tk.W)
        col_btn_frame = tk.Frame(frm_ck)
        col_btn_frame.pack(fill=tk.X, pady=(5, 15))
        
        self.btn_pick_screen = tk.Button(col_btn_frame, text="🔍 Picker", command=self.activate_picker)
        self.btn_pick_screen.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self.btn_eraser = tk.Button(col_btn_frame, text="✏ Eraser", command=self.activate_eraser)
        self.btn_eraser.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        self.btn_pick_custom = tk.Button(col_btn_frame, text="🎨 Color", command=self.pick_custom_color)
        self.btn_pick_custom.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        self.lbl_color_preview = tk.Label(frm_ck, text="Current Color", bg=self.key_color_hex, fg="black", relief="sunken")
        self.lbl_color_preview.pack(fill=tk.X, pady=(0, 10))

        self.frm_eraser_size = tk.Frame(frm_ck)
        self.frm_eraser_size.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.frm_eraser_size, text="Eraser Size:").pack(side=tk.LEFT)
        self.var_eraser_size = tk.IntVar(value=20)
        tk.Scale(self.frm_eraser_size, from_=5, to=100, variable=self.var_eraser_size, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.var_apply_despill = tk.BooleanVar(value=False) 
        chk_ds = tk.Checkbutton(frm_ck, text="Auto-Apply Despill", variable=self.var_apply_despill, command=self.trigger_update, font=("Arial", 10, "bold"), bg="#ffffe0", relief="solid", bd=1)
        chk_ds.pack(fill=tk.X, pady=(0, 5), ipady=3)
        
        self.var_apply_alpha = tk.BooleanVar(value=False)
        chk_ae = tk.Checkbutton(frm_ck, text="Auto-Apply Alpha Extract", variable=self.var_apply_alpha, command=self.trigger_update, font=("Arial", 10, "bold"), bg="#e0e0ff", relief="solid", bd=1)
        chk_ae.pack(fill=tk.X, pady=(0, 15), ipady=3)
        ttk.Label(frm_ck, text="(Uses settings from respective tabs)", font=("Arial", 8)).pack(anchor=tk.W, pady=(0,10))


        def make_slider(parent, label, min_v, max_v, default, var):
            lbl = ttk.Label(parent, text=f"{label}: {default}")
            lbl.pack(anchor=tk.W, pady=(5,0))
            def on_slide(val):
                lbl.config(text=f"{label}: {float(val):.1f}")
                self.trigger_update()
            s = ttk.Scale(parent, from_=min_v, to=max_v, variable=var, command=on_slide)
            s.pack(fill=tk.X)
            return s

        self.var_ck_lower = tk.DoubleVar(value=15.0)
        make_slider(frm_ck, "Lower Tolerance", 0, 100, 15.0, self.var_ck_lower)
        self.var_ck_upper = tk.DoubleVar(value=35.0)
        make_slider(frm_ck, "Upper Tolerance", 0, 100, 35.0, self.var_ck_upper)
        ttk.Separator(frm_ck, orient='horizontal').pack(fill='x', pady=15)
        self.var_ck_high = tk.DoubleVar(value=100.0)
        make_slider(frm_ck, "Highlights", 0, 200, 100.0, self.var_ck_high)
        self.var_ck_shadow = tk.DoubleVar(value=100.0)
        make_slider(frm_ck, "Shadows", 0, 200, 100.0, self.var_ck_shadow)
        ttk.Separator(frm_ck, orient='horizontal').pack(fill='x', pady=15)
        self.var_ck_invert = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_ck, text="Invert Mask", variable=self.var_ck_invert, command=self.trigger_update).pack(anchor=tk.W)
        self.var_ck_maskonly = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_ck, text="Show Mask Only", variable=self.var_ck_maskonly, command=self.trigger_update).pack(anchor=tk.W)

        # --- ALPHA EXTRACT TAB (NEW) ---
        self.tab_alpha = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_alpha, text='Alpha Extract')
        frm_ae = tk.Frame(self.tab_alpha, pady=10)
        frm_ae.pack(fill=tk.X)
        
        ttk.Label(frm_ae, text="Extract semi-transparent shadows/smoke", font=("Arial", 9, "italic")).pack(anchor=tk.W, pady=(0, 10))
        
        self.var_ae_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(frm_ae, text="Enable Alpha Extraction", variable=self.var_ae_enabled, command=self.trigger_update, font=("Arial", 11, "bold"), fg="purple").pack(anchor=tk.W, pady=(0, 10))
        
        # BG Brightness
        ttk.Label(frm_ae, text="Background Brightness (0-255):").pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(frm_ae, text="(Sample pure green screen area)", font=("Arial", 8)).pack(anchor=tk.W)
        self.var_ae_brightness = tk.IntVar(value=255)
        self.scale_ae_bright = tk.Scale(frm_ae, from_=1, to=255, variable=self.var_ae_brightness, orient=tk.HORIZONTAL, command=lambda v: self.trigger_update())
        self.scale_ae_bright.pack(fill=tk.X)
        
        # Edge Softness
        ttk.Label(frm_ae, text="Edge Softness:").pack(anchor=tk.W, pady=(15, 0))
        self.var_ae_softness = tk.DoubleVar(value=50.0)
        tk.Scale(frm_ae, from_=0, to=100, variable=self.var_ae_softness, orient=tk.HORIZONTAL, command=lambda v: self.trigger_update()).pack(fill=tk.X)
        
        ttk.Separator(frm_ae, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(frm_ae, text="Tip: Works best with clean green screen\nand uniform lighting.", font=("Arial", 8), foreground="gray").pack(anchor=tk.W)

        self.notebook.add(self.tab_despill, text='Despill Settings')

        frm_ds = tk.Frame(self.tab_despill, pady=10)
        frm_ds.pack(fill=tk.X)
        ttk.Label(frm_ds, text="Spill Color:").pack(anchor=tk.W)
        self.var_ds_color = tk.StringVar(value="Green")
        ttk.Radiobutton(frm_ds, text="Green", variable=self.var_ds_color, value="Green", command=self.trigger_update).pack(anchor=tk.W)
        ttk.Radiobutton(frm_ds, text="Blue", variable=self.var_ds_color, value="Blue", command=self.trigger_update).pack(anchor=tk.W)
        ttk.Label(frm_ds, text="Despill Algorithm:").pack(anchor=tk.W, pady=(15,0))
        self.var_ds_method = tk.StringVar(value="Average")
        methods = ["Average", "Double Red", "Double Average", "Limit"]
        ds_menu = ttk.OptionMenu(frm_ds, self.var_ds_method, "Average", *methods, command=lambda _: self.trigger_update())
        ds_menu.pack(fill=tk.X)
        self.var_ds_luma = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_ds, text="Preserve Luminance", variable=self.var_ds_luma, command=self.trigger_update).pack(anchor=tk.W, pady=20)

        # --- RIGHT SIDE ---
        self.right_frame = tk.Frame(content, bg="#333333")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.right_frame, bg="#333333", highlightthickness=0, cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click) 
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag) 
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release) 
        self.canvas.bind("<Motion>", self.on_canvas_motion)  # Track mouse for eraser cursor

        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<MouseWheel>", self.on_zoom)   
        self.canvas.bind("<Button-4>", self.on_zoom)     
        self.canvas.bind("<Button-5>", self.on_zoom)     

        # --- VIEW MODE TOOLBAR (NEW) ---
        view_frame = tk.Frame(self.right_frame, bg="#555555", height=30)
        view_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(view_frame, text="View Background:", bg="#555555", fg="white").pack(side=tk.LEFT, padx=10)
        
        self.var_view = tk.StringVar(value="Checker")
        
        def set_view():
            self.view_mode = self.var_view.get()
            self.redraw_canvas()

        tk.Radiobutton(view_frame, text="🏁 Checker", variable=self.var_view, value="Checker", command=set_view, bg="#555555", fg="white", selectcolor="#777777", activebackground="#666666", activeforeground="white").pack(side=tk.LEFT)
        tk.Radiobutton(view_frame, text="⬛ Black", variable=self.var_view, value="Black", command=set_view, bg="#555555", fg="white", selectcolor="#777777", activebackground="#666666", activeforeground="white").pack(side=tk.LEFT)
        tk.Radiobutton(view_frame, text="⬜ White", variable=self.var_view, value="White", command=set_view, bg="#555555", fg="white", selectcolor="#777777", activebackground="#666666", activeforeground="white").pack(side=tk.LEFT)
        tk.Radiobutton(view_frame, text="🔲 Alpha", variable=self.var_view, value="Alpha", command=set_view, bg="#555555", fg="white", selectcolor="#777777", activebackground="#666666", activeforeground="white").pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Ready. Please open an image.")
        tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, bg="#f0f0f0").pack(side=tk.BOTTOM, fill=tk.X)

        self.ui_ready = True
        self.update_color_preview()

    # --- VIEWPORT ---

    def on_pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_pan_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_zoom(self, event):
        if not self.processed_preview: return
        delta = 0
        if event.num == 5 or event.delta < 0: delta = -1 
        elif event.num == 4 or event.delta > 0: delta = 1 
        zoom_factor = 1.1
        if delta > 0: self.zoom_scale *= zoom_factor
        elif delta < 0: self.zoom_scale /= zoom_factor
        if self.zoom_scale < 0.1: self.zoom_scale = 0.1
        if self.zoom_scale > 10.0: self.zoom_scale = 10.0
        self.redraw_canvas()

    # --- TOOLS ---

    def reset_tools(self):
        self.picking_mode = False
        self.erasing_mode = False
        self.canvas.config(cursor="arrow")
        self.btn_pick_screen.config(relief="raised", bg="SystemButtonFace")
        self.btn_eraser.config(relief="raised", bg="SystemButtonFace")
        # Hide eraser cursor circle
        self.canvas.delete("eraser_cursor")


    def activate_picker(self):
        if not self.preview_image: return
        self.reset_tools()
        self.picking_mode = True
        self.canvas.config(cursor="crosshair")
        self.status_var.set("PICKER: Click image to sample color.")
        self.btn_pick_screen.config(relief="sunken", bg="#cccccc")

    def activate_eraser(self):
        if not self.preview_image: return
        self.reset_tools()
        self.erasing_mode = True
        self.canvas.config(cursor="dot") # Dot cursor
        self.status_var.set("ERASER: Click and drag to erase pixels.")
        self.btn_eraser.config(relief="sunken", bg="#cccccc")

    def pick_custom_color(self):
        self.reset_tools()
        color = colorchooser.askcolor(color=self.key_color_hex)
        if color[1]: self.set_key_color(color[1])

    # --- INTERACTION ---

    def get_image_coords(self, event_x, event_y):
        cx = self.canvas.canvasx(event_x)
        cy = self.canvas.canvasy(event_y)
        bbox = self.canvas.bbox(self.canvas_image_id) 
        if not bbox: return None
        
        img_x_start, img_y_start = bbox[0], bbox[1]
        rel_x = cx - img_x_start
        rel_y = cy - img_y_start
        
        orig_x = int(rel_x / self.zoom_scale)
        orig_y = int(rel_y / self.zoom_scale)
        return (orig_x, orig_y)

    def on_canvas_click(self, event):
        if not self.preview_image: return
        coords = self.get_image_coords(event.x, event.y)
        if not coords: return
        x, y = coords

        if self.picking_mode:
            w, h = self.preview_image.size
            if 0 <= x < w and 0 <= y < h:
                try:
                    pixel = self.preview_image.getpixel((x, y))
                    hex_col = '#{:02x}{:02x}{:02x}'.format(pixel[0], pixel[1], pixel[2])
                    self.reset_tools()
                    self.set_key_color(hex_col)
                except: pass
        
        elif self.erasing_mode:
            self.apply_eraser(x, y)

    def on_canvas_drag(self, event):
        if self.erasing_mode:
            coords = self.get_image_coords(event.x, event.y)
            if coords:
                self.apply_eraser(coords[0], coords[1])
            # Update eraser cursor position during drag
            self.update_eraser_cursor(event.x, event.y)

    def on_canvas_release(self, event):
        if self.erasing_mode:
            self.trigger_update()

    def on_canvas_motion(self, event):
        """Track mouse movement for eraser cursor visualization"""
        if self.erasing_mode:
            self.update_eraser_cursor(event.x, event.y)
        else:
            # Not in erasing mode, hide cursor
            self.canvas.delete("eraser_cursor")

    def update_eraser_cursor(self, x, y):
        """Draw/update the eraser cursor circle at mouse position"""
        size = self.var_eraser_size.get() * self.zoom_scale
        cx = self.canvas.canvasx(x)
        cy = self.canvas.canvasy(y)
        
        # Delete old cursor and draw new one
        self.canvas.delete("eraser_cursor")
        self.canvas.create_oval(
            cx - size/2, cy - size/2,
            cx + size/2, cy + size/2,
            outline="red", width=2, tags="eraser_cursor"
        )


    def apply_eraser(self, x, y):
        size = self.var_eraser_size.get()
        draw_prev = ImageDraw.Draw(self.preview_mask)
        draw_prev.ellipse([x-size/2, y-size/2, x+size/2, y+size/2], fill=0)

        scale_x = self.original_image.width / self.preview_image.width
        scale_y = self.original_image.height / self.preview_image.height
        
        fx, fy = x * scale_x, y * scale_y
        fsize = size * scale_x 
        draw_full = ImageDraw.Draw(self.manual_mask)
        draw_full.ellipse([fx-fsize/2, fy-fsize/2, fx+fsize/2, fy+fsize/2], fill=0)

        if self.processed_preview:
            curr = self.processed_preview.copy()
            r, g, b, a = curr.split()
            new_a = ImageChops.multiply(a, self.preview_mask)
            curr.putalpha(new_a)
            self.processed_preview = curr
            self.redraw_canvas()

    def auto_crop(self):
        if not self.original_image or not self.manual_mask: return
        
        self.status_var.set("Cropping... Please wait.")
        self.root.update()

        params = self.get_params()
        res = self.process_logic(self.original_image.copy(), params, -1)
        if not res: return

        try:
            bbox = res.getchannel('A').getbbox()
        except:
            bbox = res.split()[-1].getbbox()
        
        if bbox:
            self.original_image = self.original_image.crop(bbox)
            self.manual_mask = self.manual_mask.crop(bbox)
            
            self.preview_image = self.original_image.copy()
            self.preview_image.thumbnail((400, 400))
            
            self.preview_mask = self.manual_mask.copy()
            self.preview_mask = self.preview_mask.resize(self.preview_image.size, Image.Resampling.NEAREST)

            self.zoom_scale = 1.0
            self.trigger_update()
            messagebox.showinfo("Crop", "Image cropped to visible content.")
            self.status_var.set("Cropped.")
        else:
            messagebox.showwarning("Crop", "Image seems fully transparent, cannot crop.")

    # --- MAIN LOGIC ---

    def set_key_color(self, hex_code):
        self.key_color_hex = hex_code
        self.var_apply_chroma.set(True)
        self.var_apply_despill.set(True)
        self.update_color_preview()
        self.trigger_update()

    def update_color_preview(self):
        rgb = ImageColor.getrgb(self.key_color_hex)
        brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
        txt = "black" if brightness > 125 else "white"
        self.lbl_color_preview.config(bg=self.key_color_hex, fg=txt, text=f"Key: {self.key_color_hex}")

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path: return
        try:
            self.original_image = Image.open(path).convert("RGBA")
            self.manual_mask = Image.new("L", self.original_image.size, 255)
            self.preview_image = self.original_image.copy()
            self.preview_image.thumbnail((400, 400))
            self.preview_mask = Image.new("L", self.preview_image.size, 255)
            self.status_var.set(f"Loaded {path}")
            self.zoom_scale = 1.0
            self.trigger_update()
        except Exception as e: messagebox.showerror("Error", str(e))

    def on_tab_change(self, event):
        tab_id = self.notebook.index(self.notebook.select())
        if tab_id == 0:
            self.current_mode = "Chroma"
        elif tab_id == 1:
            self.current_mode = "AlphaExtract"
        else:
            self.current_mode = "Despill"

        self.trigger_update()

    def get_params(self):
        return {
            'mode': self.current_mode,
            'apply_chroma': self.var_apply_chroma.get(),
            'apply_despill': self.var_apply_despill.get(),
            'ds_color': self.var_ds_color.get(),
            'ds_method': self.var_ds_method.get(),
            'ds_luma': self.var_ds_luma.get(),
            'ck_color': self.key_color_hex,
            'ck_low': self.var_ck_lower.get(),
            'ck_high': self.var_ck_upper.get(),
            'ck_shadow': self.var_ck_shadow.get(),
            'ck_highlight': self.var_ck_high.get(),
            'ck_invert': self.var_ck_invert.get(),
            'ck_maskonly': self.var_ck_maskonly.get(),
            # Alpha Extract params
            'ae_enabled': self.var_ae_enabled.get(),
            'ae_brightness': self.var_ae_brightness.get(),
            'ae_softness': self.var_ae_softness.get(),
            'apply_alpha': self.var_apply_alpha.get()
        }



    def process_logic(self, img_obj, params, job_id):
        monitor = self if job_id != -1 else None

        if params['mode'] == 'Chroma':
            if params['apply_chroma']:
                k_lab = hex_to_lab(params['ck_color'])
                img_obj = run_chromakey(
                    img_obj, k_lab, 
                    params['ck_low'], params['ck_high'], 
                    params['ck_shadow'], params['ck_highlight'], 
                    params['ck_invert'], params['ck_maskonly'],
                    app_ref=monitor, job_id=job_id
                )
                if img_obj is None: return None
            
            if params['apply_alpha'] and not params['ck_maskonly']:
                img_obj = run_alpha_extract(
                    img_obj, params['ck_color'],
                    params['ae_brightness'], params['ae_softness'],
                    app_ref=monitor, job_id=job_id
                )
                if img_obj is None: return None
            
            if params['apply_despill'] and not params['ck_maskonly']:
                img_obj = run_despill(
                    img_obj, params['ds_color'], params['ds_method'], params['ds_luma'],
                    app_ref=monitor, job_id=job_id
                )

        
        elif params['mode'] == 'AlphaExtract':
            if params['ae_enabled']:
                img_obj = run_alpha_extract(
                    img_obj, params['ck_color'],
                    params['ae_brightness'], params['ae_softness'],
                    app_ref=monitor, job_id=job_id
                )
                if img_obj is None:
                    return None
        
        elif params['mode'] == 'Despill':
            img_obj = run_despill(
                img_obj, params['ds_color'], params['ds_method'], params['ds_luma'],
                app_ref=monitor, job_id=job_id
            )

        if img_obj:
            mask_to_use = None
            if job_id == -1: 
                mask_to_use = self.manual_mask
            else:
                mask_to_use = self.preview_mask

            if mask_to_use:
                if mask_to_use.size != img_obj.size:
                    mask_to_use = mask_to_use.resize(img_obj.size)
                
                r, g, b, a = img_obj.split()
                new_a = ImageChops.multiply(a, mask_to_use)
                img_obj.putalpha(new_a)

        return img_obj

    def trigger_update(self):
        if not self.ui_ready or not self.preview_image: return
        self.current_job_id += 1
        self.pending_params = self.get_params()
        if not self.is_processing:
            self.status_var.set("Processing...")
            self.is_processing = True
            threading.Thread(target=self.bg_worker, daemon=True).start()

    def bg_worker(self):
        while self.pending_params:
            current_params = self.pending_params
            this_job_id = self.current_job_id
            self.pending_params = None
            res_img = self.process_logic(self.preview_image.copy(), current_params, this_job_id)
            if res_img is not None and this_job_id == self.current_job_id:
                self.processed_preview = res_img 
                self.root.after(0, self.redraw_canvas)
        
        self.is_processing = False
        self.root.after(0, lambda: self.status_var.set("Ready."))

    def redraw_canvas(self):
        if not self.processed_preview: return
        orig_w, orig_h = self.processed_preview.size
        new_w = int(orig_w * self.zoom_scale)
        new_h = int(orig_h * self.zoom_scale)
        zoomed_img = self.processed_preview.resize((new_w, new_h), Image.Resampling.BILINEAR)
        
        # --- VIEW MODE LOGIC ---
        bg = None
        if self.view_mode == "Checker":
            bg = Image.new('RGBA', (new_w, new_h), (204, 204, 204, 255))
            draw = ImageDraw.Draw(bg)
            tile = int(20 * self.zoom_scale) 
            if tile < 5: tile = 5 
            for x in range(0, new_w, tile):
                for y in range(0, new_h, tile):
                    if (x // tile + y // tile) % 2 == 0:
                        draw.rectangle([x, y, x+tile, y+tile], fill=(153, 153, 153, 255))
            bg.alpha_composite(zoomed_img)

        elif self.view_mode == "Black":
            bg = Image.new('RGBA', (new_w, new_h), (0, 0, 0, 255))
            bg.alpha_composite(zoomed_img)

        elif self.view_mode == "White":
            bg = Image.new('RGBA', (new_w, new_h), (255, 255, 255, 255))
            bg.alpha_composite(zoomed_img)

        elif self.view_mode == "Alpha":
            # Extract Alpha and show as grayscale
            try:
                alpha = zoomed_img.getchannel('A')
            except:
                alpha = zoomed_img.split()[-1]
            bg = alpha.convert("RGBA") # Convert grayscale mask to RGBA for Tkinter
        
        self.tk_img = ImageTk.PhotoImage(bg)
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if self.canvas_image_id is None:
            self.canvas_image_id = self.canvas.create_image(cw//2, ch//2, image=self.tk_img)
        else:
            self.canvas.itemconfig(self.canvas_image_id, image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def save_image(self):
        if not self.original_image: return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path: return
        self.btn_save.config(state=tk.DISABLED, text="Saving...")
        self.status_var.set("Processing Full Resolution...")
        params = self.get_params()
        threading.Thread(target=self.bg_save, args=(path, params, -1), daemon=True).start()

    def bg_save(self, path, params, job_id):
        try:
            final = self.process_logic(self.original_image.copy(), params, job_id)
            if final:
                final.save(path, "PNG")
                self.root.after(0, lambda: self.save_finished(path, None))
            else:
                self.root.after(0, lambda: self.save_finished(None, "Process aborted."))
        except Exception as e:
            self.root.after(0, lambda: self.save_finished(None, str(e)))

    def save_finished(self, path, error):
        self.btn_save.config(state=tk.NORMAL, text="💾 Save PNG")
        if error:
            messagebox.showerror("Error", error)
            self.status_var.set("Error saving.")
        else:
            messagebox.showinfo("Success", f"Saved to {path}")
            self.status_var.set(f"Saved to {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyingApp(root)
    root.mainloop()