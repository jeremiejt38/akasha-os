#!/usr/bin/env python3
"""Generate shutdown/reboot splash images with bottom text overlay."""

from PIL import Image, ImageDraw, ImageFont
import os
import sys

MEDIA_DIR = "/storage/.kodi/media"
SPLASH = os.path.join(MEDIA_DIR, "splash.png")
FONT_SIZE = 130

# Try to find a usable font
def find_font():
    candidates = [
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Fallback to default
    return None


def fit_font_size(draw, font_path, text, max_font=160, min_font=80, width=1920):
    """Return the largest font size for which text fits inside width with a margin."""
    if not font_path:
        return min_font
    size = max_font
    while size >= min_font:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        if tw <= width - 120:
            return size
        size -= 4
    return min_font


def add_text(image_path, text, output_path, font_size=None):
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_path = find_font()
    w, h = img.size

    if font_path:
        if font_size:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = (w - tw) / 2
    y = h - th - 120  # 120px from bottom

    # Semi-transparent dark bar behind text for readability
    bar_height = th + 60
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, h - bar_height - 40, w, h], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    # Black shadow
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 255))
    # White text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    # Convert to RGB for JPEG/PNG compatibility
    rgb = Image.new("RGB", img.size, (0, 0, 0))
    rgb.paste(img, mask=img.split()[3])
    rgb.save(output_path, "PNG")
    print(f"Generated: {output_path}")


def main():
    if not os.path.isdir(MEDIA_DIR):
        print(f"Directory {MEDIA_DIR} does not exist")
        sys.exit(1)

    base = SPLASH if os.path.exists(SPLASH) else None
    if not base:
        # Fallback to the splash screen if available
        alt = os.path.join(MEDIA_DIR, "akasha-os-splash-screen.png")
        if os.path.exists(alt):
            base = alt
        else:
            print("No splash base image found")
            sys.exit(1)

    # Find the largest font size that fits the longest text
    longest = "Redémarrage en cours..."
    font_path = find_font()
    img = Image.open(base).convert("RGBA")
    draw = ImageDraw.Draw(img)
    best_size = fit_font_size(draw, font_path, longest, max_font=40, min_font=30)

    add_text(base, "Arrêt en cours...", os.path.join(MEDIA_DIR, "splash-shutdown.png"), font_size=best_size)
    add_text(base, "Redémarrage en cours...", os.path.join(MEDIA_DIR, "splash-reboot.png"), font_size=best_size)


if __name__ == "__main__":
    main()
