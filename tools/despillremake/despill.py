import argparse
import sys
from PIL import Image

# Standard Rec.709 Luma Coefficients
LUMA_COEFF_R = 0.2126
LUMA_COEFF_G = 0.7152
LUMA_COEFF_B = 0.0722

def clamp_uint8(value):
    """Helper to ensure value stays between 0 and 255 and is an integer."""
    return int(max(0, min(255, value)))

def process_despill_pure(image_path, output_path, key_color, method, preserve_luma):
    print("Loading image...")
    try:
        img = Image.open(image_path).convert('RGBA')
    except Exception as e:
        print(f"Error loading image: {e}")
        sys.exit(1)

    width, height = img.size
    pixels = img.load() # Creates a pixel access object
    
    print(f"Processing {width}x{height} pixels... (This may take a moment without NumPy)")

    # Loop through every single pixel
    for x in range(width):
        for y in range(height):
            # Get pixel data (0-255 integers)
            r_int, g_int, b_int, a_int = pixels[x, y]

            # Convert to float (0.0 - 1.0) to match GLSL precision
            r = r_int / 255.0
            g = g_int / 255.0
            b = b_int / 255.0
            
            # Store original for luma calc
            orig_r, orig_g, orig_b = r, g, b
            
            limit = 0.0

            # --- GREEN SCREEN LOGIC ---
            if key_color == 'green':
                if method == 'average':
                    limit = (r + b) / 2.0
                elif method == 'double_red':
                    limit = (2.0 * r + b) / 3.0
                elif method == 'double_average':
                    limit = (2.0 * b + r) / 3.0
                elif method == 'limit':
                    limit = b
                
                # Apply: Green cannot be higher than limit
                if g > limit:
                    g = limit

            # --- BLUE SCREEN LOGIC ---
            elif key_color == 'blue':
                if method == 'average':
                    limit = (r + g) / 2.0
                elif method == 'double_red':
                    limit = (2.0 * r + g) / 3.0
                elif method == 'double_average':
                    limit = (2.0 * g + r) / 3.0
                elif method == 'limit':
                    limit = g
                
                # Apply: Blue cannot be higher than limit
                if b > limit:
                    b = limit

            # --- PRESERVE LUMINANCE LOGIC ---
            if preserve_luma:
                # GLSL: vec4 diff = original_col - tex_col;
                diff_r = orig_r - r
                diff_g = orig_g - g
                diff_b = orig_b - b

                # GLSL: dot(abs(diff.rgb), luma_coeffs);
                # We use abs() to match the C++ implementation exactly
                luma = (abs(diff_r) * LUMA_COEFF_R) + \
                       (abs(diff_g) * LUMA_COEFF_G) + \
                       (abs(diff_b) * LUMA_COEFF_B)

                # Add luma back
                r += luma
                g += luma
                b += luma

            # Convert back to 0-255 integer
            pixels[x, y] = (
                clamp_uint8(r * 255),
                clamp_uint8(g * 255),
                clamp_uint8(b * 255),
                a_int # Alpha remains unchanged
            )

    print(f"Saving to {output_path}...")
    img.save(output_path)
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Despill PNG (Pure Python Version)")
    
    parser.add_argument("input", help="Input PNG file path")
    parser.add_argument("output", help="Output PNG file path")
    
    parser.add_argument("-k", "--key-color", 
                        choices=['green', 'blue'], 
                        default='green',
                        help="The background color to remove spill from")
    
    parser.add_argument("-m", "--method", 
                        choices=['average', 'double_red', 'double_average', 'limit'], 
                        default='average',
                        help="The despill algorithm to use")
    
    parser.add_argument("-p", "--preserve-luminance", 
                        action='store_true', 
                        help="Attempt to restore brightness")

    args = parser.parse_args()

    process_despill_pure(args.input, args.output, args.key_color, args.method, args.preserve_luminance)