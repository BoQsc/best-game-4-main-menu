import argparse
import math
import sys
from PIL import Image, ImageColor

# --- Constants from Olive Shader ---
Xn = 95.0489
Yn = 100.0
Zn = 108.8840
DELTA = 0.20689655172  # 6/29
DELTA_3 = DELTA ** 3   # pow(delta, 3.0)
DELTA_2 = DELTA ** 2   # pow(delta, 2)

def linearize_srgb(v):
    """
    Converts sRGB (0.0-1.0) to Linear RGB.
    This mimics the 'SceneLinear' input expected by the Olive shader.
    """
    if v <= 0.04045:
        return v / 12.92
    else:
        return ((v + 0.055) / 1.055) ** 2.4

def func_lab(t):
    """
    The helper function from the GLSL shader:
    float func(float t) { ... }
    """
    if t > DELTA_3:
        return t ** (1.0 / 3.0)
    else:
        return (t / (3.0 * DELTA_2)) + (4.0 / 29.0)

def rgb_to_xyz(r, g, b):
    """
    Converts Linear RGB to CIE XYZ (D65).
    Standard Matrix for sRGB/Rec709.
    """
    # Matrix multiplication
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) * 100.0
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) * 100.0
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) * 100.0
    return x, y, z

def xyz_to_lab(x, y, z):
    """
    Converts CIE XYZ to Lab using the shader constants.
    vec4 CIExyz_to_Lab(vec4 CIE)
    """
    l_val = 116.0 * func_lab(y / Yn) - 16.0
    a_val = 500.0 * (func_lab(x / Xn) - func_lab(y / Yn))
    b_val = 200.0 * (func_lab(y / Yn) - func_lab(z / Zn))
    return l_val, a_val, b_val

def get_lab_color(r, g, b):
    """Composite helper to go straight from sRGB to Lab"""
    # 1. Linearize
    lin_r = linearize_srgb(r)
    lin_g = linearize_srgb(g)
    lin_b = linearize_srgb(b)
    # 2. To XYZ
    x, y, z = rgb_to_xyz(lin_r, lin_g, lin_b)
    # 3. To Lab
    return xyz_to_lab(x, y, z)

def process_chromakey(args):
    print(f"Opening {args.input}...")
    try:
        img = Image.open(args.input).convert("RGBA")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Prepare Garbage/Core mattes if they exist
    garbage_img = None
    core_img = None
    
    if args.garbage_matte:
        try:
            garbage_img = Image.open(args.garbage_matte).convert("L").resize(img.size)
            print("Loaded Garbage Matte.")
        except:
            print("Warning: Could not load Garbage Matte.")

    if args.core_matte:
        try:
            core_img = Image.open(args.core_matte).convert("L").resize(img.size)
            print("Loaded Core Matte.")
        except:
            print("Warning: Could not load Core Matte.")

    # Parse Key Color
    # ImageColor.getrgb returns (r, g, b) 0-255
    key_rgb_255 = ImageColor.getrgb(args.color)
    # Convert Key to Lab immediately (0.0 - 1.0 input)
    key_lab = get_lab_color(key_rgb_255[0]/255.0, key_rgb_255[1]/255.0, key_rgb_255[2]/255.0)

    width, height = img.size
    pixels = img.load()
    
    # Access for mattes if they exist
    garbage_pixels = garbage_img.load() if garbage_img else None
    core_pixels = core_img.load() if core_img else None

    print(f"Processing {width}x{height} pixels. Please wait...")

    # Main Loop
    for x in range(width):
        for y in range(height):
            # Get Source pixel
            r255, g255, b255, a255 = pixels[x, y]

            # Normalize to 0.0 - 1.0
            r, g, b, a = r255/255.0, g255/255.0, b255/255.0, a255/255.0

            # 1. Un-premultiply Alpha (Shader logic)
            # if (unassoc.a > 0) { unassoc.rgb /= unassoc.a; }
            if a > 0:
                r_unassoc = r / a
                g_unassoc = g / a
                b_unassoc = b / a
            else:
                r_unassoc, g_unassoc, b_unassoc = r, g, b

            # 2. Convert Pixel to Lab
            pixel_lab = get_lab_color(r_unassoc, g_unassoc, b_unassoc)

            # 3. Calculate Distance (Euclidean in Lab space)
            # float colorclose(...)
            # temp = sqrt(((key.g-col.g)^2) + ((key.b-col.b)^2) + ((key.r-col.r)^2));
            # Note: Lab map: L=x, a=y, b=z in tuple
            diff_L = key_lab[0] - pixel_lab[0]
            diff_a = key_lab[1] - pixel_lab[1]
            diff_b = key_lab[2] - pixel_lab[2]
            
            dist = math.sqrt(diff_L**2 + diff_a**2 + diff_b**2)

            # 4. Calculate Mask based on tolerance
            # if (temp < tola) return 0.0
            # if (temp < tolb) return (temp-tola)/(tolb-tola)
            mask = 1.0
            if dist < args.lower:
                mask = 0.0
            elif dist < args.upper:
                mask = (dist - args.lower) / (args.upper - args.lower)
            
            # Clamp mask
            mask = max(0.0, min(1.0, mask))

            # 5. Apply Mattes
            if garbage_pixels:
                # Garbage removes from mask (assumes white in matte = garbage)
                g_val = garbage_pixels[x, y] / 255.0
                mask -= g_val
                mask = max(0.0, min(1.0, mask))
            
            if core_pixels:
                # Core adds to mask (assumes white in matte = keep)
                c_val = core_pixels[x, y] / 255.0
                mask += c_val
                mask = max(0.0, min(1.0, mask))

            # 6. Highlights / Shadows (Levels adjustments)
            # mask = shadows * 0.01 * (highlights * 0.01 * mask - 1.0) + 1.0
            # Note: Input args are typically 0-100 floats
            mask = args.shadows * 0.01 * (args.highlights * 0.01 * mask - 1.0) + 1.0
            mask = max(0.0, min(1.0, mask))

            # 7. Invert
            if args.invert:
                mask = 1.0 - mask

            # 8. Output Composition
            if args.mask_only:
                val = int(mask * 255)
                pixels[x, y] = (val, val, val, 255)
            else:
                # Apply mask to original alpha
                # The shader does: col *= mask. 
                # Since we are outputting RGBA, we multiply the Alpha channel.
                new_a = int(a255 * mask)
                pixels[x, y] = (r255, g255, b255, new_a)

    print(f"Saving to {args.output}...")
    img.save(args.output)
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chroma Key Tool (Olive Editor Logic)")
    
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")
    
    parser.add_argument("-c", "--color", default="#00FF00", 
                        help="Key color in Hex (e.g. #00FF00 or #0000FF). Default Green.")

    parser.add_argument("--lower", type=float, default=5.0, 
                        help="Lower Tolerance (Clip Black). Distance below this is fully transparent.")
    parser.add_argument("--upper", type=float, default=25.0, 
                        help="Upper Tolerance (Clip White). Distance above this is fully opaque.")
    
    parser.add_argument("--highlights", type=float, default=100.0, 
                        help="Highlights adjustment (0.0 - 100.0+)")
    parser.add_argument("--shadows", type=float, default=100.0, 
                        help="Shadows adjustment (0.0 - 100.0+)")

    parser.add_argument("--garbage-matte", help="Path to garbage matte image (removes from result)")
    parser.add_argument("--core-matte", help="Path to core matte image (keeps in result)")

    parser.add_argument("--mask-only", action="store_true", help="Output grayscale mask only")
    parser.add_argument("--invert", action="store_true", help="Invert the final mask")

    args = parser.parse_args()
    process_chromakey(args)