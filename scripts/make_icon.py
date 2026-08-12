"""Generate the application icon (assets/app_icon.ico).

Committed as a script rather than a binary blob so the icon can be regenerated
or restyled without a design tool. Windows shows this icon in Explorer, the
taskbar and the SmartScreen prompt, and a real icon is one of the signals that
separates a legitimate application from an anonymous binary.

Usage:  python scripts/make_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - build-time helper
    raise SystemExit("Pillow is required. Run: python -m pip install pillow") from None


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "assets" / "app_icon.ico"

# Rendered at the largest size, then downsampled, so small sizes stay crisp.
MASTER_SIZE = 512
ICON_SIZES = [(size, size) for size in (16, 24, 32, 48, 64, 128, 256)]

BACKGROUND = (226, 72, 59, 255)     # brand red, matches --c-accent
BACKGROUND_DEEP = (169, 44, 34, 255)
GLYPH_COLOR = (255, 252, 245, 255)
GLYPH = "学"

# Windows CJK faces, most preferred first.
FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/Deng.ttf",
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | None:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return None


def _vertical_gradient(size: int, top: tuple[int, ...], bottom: tuple[int, ...]) -> Image.Image:
    gradient = Image.new("RGBA", (1, size))
    for y in range(size):
        ratio = y / max(1, size - 1)
        gradient.putpixel(
            (0, y),
            tuple(int(top[channel] + (bottom[channel] - top[channel]) * ratio) for channel in range(4)),
        )
    return gradient.resize((size, size))


def build_master() -> Image.Image:
    canvas = Image.new("RGBA", (MASTER_SIZE, MASTER_SIZE), (0, 0, 0, 0))

    # Rounded-square plate with a subtle vertical gradient.
    mask = Image.new("L", (MASTER_SIZE, MASTER_SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, MASTER_SIZE - 1, MASTER_SIZE - 1), radius=int(MASTER_SIZE * 0.22), fill=255
    )
    plate = _vertical_gradient(MASTER_SIZE, BACKGROUND, BACKGROUND_DEEP)
    canvas.paste(plate, (0, 0), mask)

    draw = ImageDraw.Draw(canvas)
    font = _load_font(int(MASTER_SIZE * 0.62))
    if font is None:
        # No CJK font available: fall back to a bold latin monogram so the build
        # still produces a usable icon.
        fallback = ImageFont.load_default()
        draw.text((MASTER_SIZE // 2, MASTER_SIZE // 2), "HSK", font=fallback, fill=GLYPH_COLOR, anchor="mm")
        return canvas

    box = draw.textbbox((0, 0), GLYPH, font=font)
    x = (MASTER_SIZE - (box[2] - box[0])) / 2 - box[0]
    y = (MASTER_SIZE - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), GLYPH, font=font, fill=GLYPH_COLOR)
    return canvas


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    master = build_master()
    master.save(OUTPUT_FILE, format="ICO", sizes=ICON_SIZES)
    master.resize((256, 256), Image.LANCZOS).save(
        OUTPUT_FILE.with_suffix(".png"), format="PNG"
    )
    print(f"Wrote {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size:,} bytes)")
    print(f"Wrote {OUTPUT_FILE.with_suffix('.png')}")


if __name__ == "__main__":
    sys.exit(main())
