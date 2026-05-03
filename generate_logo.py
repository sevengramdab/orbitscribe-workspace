"""Generate OrbitScribe logo with orbital rings and microphone."""

from PIL import Image, ImageDraw
import math
import os

# Brand colors
IDLE = (139, 92, 246)          # Purple (#8B5CF6)
IDLE_BRIGHT = (167, 139, 250)  # Light purple (#A78BFA)
IDLE_RING = (124, 58, 237)     # Violet ring (#7C3AED)
RECORDING = (249, 115, 22)     # Orange (#F97316)
RECORDING_BRIGHT = (251, 146, 60)  # Light orange (#FB923C)
RECORDING_RING = (234, 88, 12)     # Dark orange ring (#EA580C)

def draw_logo(size=512, mode="idle", bg_circle=True):
    """Draw the OrbitScribe logo."""
    if mode == "idle":
        dom = IDLE
        bright = IDLE_BRIGHT
        ring = IDLE_RING
    else:
        dom = RECORDING
        bright = RECORDING_BRIGHT
        ring = RECORDING_RING

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 512.0
    cx, cy = size // 2, size // 2

    if bg_circle:
        margin = int(12 * s)
        for r in range(int(60 * s), 0, -2):
            alpha = max(0, min(255, int(30 - r * 0.3)))
            draw.ellipse(
                [cx - int(236*s) - r, cy - int(236*s) - r,
                 cx + int(236*s) + r, cy + int(236*s) + r],
                outline=(*dom, alpha), width=2
            )
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(15, 18, 28, 255),
            outline=(*dom, 180),
            width=int(3 * s)
        )

    ring_configs = [
        (220 * s, 180 * s, 25),
        (200 * s, 190 * s, -15),
        (210 * s, 170 * s, 45),
    ]
    for rx, ry, angle in ring_configs:
        points = []
        steps = 120
        for i in range(steps + 1):
            t = 2 * math.pi * i / steps
            x = rx * math.cos(t)
            y = ry * math.sin(t)
            rad = math.radians(angle)
            xr = x * math.cos(rad) - y * math.sin(rad)
            yr = x * math.sin(rad) + y * math.cos(rad)
            points.append((cx + xr, cy + yr))
        draw.line(points, fill=(*ring, 200), width=int(2.5 * s))
        highlight_idx = steps // 4
        hx, hy = points[highlight_idx]
        r = int(4 * s)
        draw.ellipse([hx-r, hy-r, hx+r, hy+r], fill=(*bright, 255))

    mic_w = int(56 * s)
    mic_h = int(90 * s)
    mic_x = cx - mic_w // 2
    mic_y = cy - mic_h // 2 - int(10 * s)
    corner = int(28 * s)
    draw.rounded_rectangle(
        [mic_x, mic_y, mic_x + mic_w, mic_y + mic_h],
        radius=corner, fill=(255, 255, 255, 255)
    )

    line_spacing = int(12 * s)
    line_y_start = mic_y + int(16 * s)
    line_w = int(32 * s)
    line_x = cx - line_w // 2
    grill_color = (200, 210, 230, 180)
    for i in range(4):
        ly = line_y_start + i * line_spacing
        draw.line([(line_x, ly), (line_x + line_w, ly)], fill=grill_color, width=int(1.5 * s))

    stand_y = mic_y + mic_h - int(8 * s)
    arc_box = [
        cx - int(44 * s), stand_y,
        cx + int(44 * s), stand_y + int(52 * s)
    ]
    draw.arc(arc_box, start=0, end=180, fill=(255, 255, 255, 255), width=int(5 * s))

    draw.line(
        [(cx, stand_y + int(20 * s)), (cx, stand_y + int(44 * s))],
        fill=(255, 255, 255, 255), width=int(5 * s)
    )

    base_y = stand_y + int(44 * s)
    base_half = int(18 * s)
    draw.line(
        [(cx - base_half, base_y), (cx + base_half, base_y)],
        fill=(255, 255, 255, 255), width=int(5 * s)
    )

    return img


def generate_svg(mode="idle"):
    if mode == "idle":
        dom, bright, ring = "#8b5cf6", "#a78bfa", "#7c3aed"
    else:
        dom, bright, ring = "#f97316", "#fb923c", "#ea580c"

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="glow{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{dom}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{bright}" stop-opacity="0.1"/>
    </linearGradient>
  </defs>
  <circle cx="256" cy="256" r="244" fill="#0f111c" stroke="{dom}" stroke-width="3" opacity="0.9"/>
  <circle cx="256" cy="256" r="244" fill="url(#glow{mode})" opacity="0.3"/>
  <g fill="none" stroke="{ring}" stroke-width="2.5" opacity="0.8">
    <ellipse cx="256" cy="256" rx="220" ry="180" transform="rotate(25 256 256)"/>
    <ellipse cx="256" cy="256" rx="200" ry="190" transform="rotate(-15 256 256)"/>
    <ellipse cx="256" cy="256" rx="210" ry="170" transform="rotate(45 256 256)"/>
  </g>
  <circle cx="356" cy="166" r="4" fill="{bright}"/>
  <circle cx="446" cy="256" r="4" fill="{bright}"/>
  <circle cx="356" cy="346" r="4" fill="{bright}"/>
  <rect x="228" y="168" width="56" height="90" rx="28" fill="white"/>
  <g stroke="#c8d2e6" stroke-width="1.5" opacity="0.5">
    <line x1="240" y1="192" x2="272" y2="192"/>
    <line x1="240" y1="204" x2="272" y2="204"/>
    <line x1="240" y1="216" x2="272" y2="216"/>
    <line x1="240" y1="228" x2="272" y2="228"/>
  </g>
  <path d="M 212 250 A 44 26 0 0 0 300 250" fill="none" stroke="white" stroke-width="5" stroke-linecap="round"/>
  <line x1="256" y1="276" x2="256" y2="294" stroke="white" stroke-width="5" stroke-linecap="round"/>
  <line x1="238" y1="294" x2="274" y2="294" stroke="white" stroke-width="5" stroke-linecap="round"/>
</svg>'''


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for mode in ("idle", "recording"):
        img = draw_logo(512, mode=mode)
        png_path = os.path.join(base_dir, f"logo_{mode}.png")
        img.save(png_path)
        print(f"Logo {mode} PNG: {png_path}")

        svg_path = os.path.join(base_dir, f"logo_{mode}.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(generate_svg(mode))
        print(f"Logo {mode} SVG: {svg_path}")

    sizes = [16, 32, 48, 64, 128, 256]
    images = [draw_logo(sz, mode="idle") for sz in sizes]
    ico_path = os.path.join(base_dir, "voice_to_text.ico")
    images[0].save(
        ico_path, format="ICO",
        sizes=[(im.width, im.height) for im in images],
        append_images=images[1:]
    )
    print(f"App ICO:  {ico_path}")

    print(f"\nIdle color:     #8b5cf6 (purple)")
    print(f"Recording color: #f97316 (orange)")


if __name__ == "__main__":
    main()
