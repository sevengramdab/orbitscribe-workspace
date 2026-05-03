"""Generate a microphone icon for the voice-to-text tool."""

from PIL import Image, ImageDraw
import math
import os

# Icon sizes for Windows .ico
SIZES = [16, 32, 48, 64, 128, 256]

def draw_microphone(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale factor
    s = size / 256.0
    
    # Background circle with gradient-like fill (solid teal/blue)
    bg_color = (0, 150, 200, 255)  # Nice teal-blue
    margin = int(8 * s)
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=bg_color,
        outline=None
    )
    
    # Microphone body (rounded rect)
    mic_color = (255, 255, 255, 255)
    body_w = int(64 * s)
    body_h = int(100 * s)
    body_x = (size - body_w) // 2
    body_y = int(70 * s)
    corner = int(32 * s)
    draw.rounded_rectangle(
        [body_x, body_y, body_x + body_w, body_y + body_h],
        radius=corner,
        fill=mic_color
    )
    
    # Microphone stand (arc at bottom)
    stand_y = body_y + body_h - int(10 * s)
    arc_box = [
        int(68 * s),
        stand_y,
        int(188 * s),
        stand_y + int(80 * s)
    ]
    draw.arc(arc_box, start=0, end=180, fill=mic_color, width=int(12 * s))
    
    # Stand vertical line
    stand_line_x = size // 2
    draw.line(
        [(stand_line_x, stand_y + int(30 * s)), (stand_line_x, stand_y + int(60 * s))],
        fill=mic_color,
        width=int(12 * s)
    )
    
    # Stand base (small horizontal line)
    base_y = stand_y + int(60 * s)
    base_half = int(24 * s)
    draw.line(
        [(stand_line_x - base_half, base_y), (stand_line_x + base_half, base_y)],
        fill=mic_color,
        width=int(12 * s)
    )
    
    return img


def main():
    images = []
    for sz in SIZES:
        images.append(draw_microphone(sz))
    
    # Save as multi-resolution ICO
    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_to_text.ico")
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(im.width, im.height) for im in images],
        append_images=images[1:]
    )
    print(f"Icon saved to: {ico_path}")


if __name__ == "__main__":
    main()
