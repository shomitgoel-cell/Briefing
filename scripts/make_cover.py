"""Generate a simple podcast cover image once, if one doesn't already exist."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COVER_PATH = Path(__file__).resolve().parent.parent / "docs" / "cover.jpg"
SIZE = 1400
BACKGROUND = (13, 27, 42)
ACCENT = (86, 156, 214)
TEXT_COLOR = (240, 240, 240)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_cover_if_missing() -> None:
    if COVER_PATH.exists():
        return

    img = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, SIZE - 220, SIZE, SIZE], fill=ACCENT)

    title_font = _load_font(120)
    subtitle_font = _load_font(56)

    draw.text((80, 480), "DAILY", font=title_font, fill=TEXT_COLOR)
    draw.text((80, 620), "BRIEFING", font=title_font, fill=TEXT_COLOR)
    draw.text((80, SIZE - 160), "Geopolitics & Markets", font=subtitle_font, fill=(20, 20, 20))

    COVER_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(COVER_PATH, format="JPEG", quality=90)


if __name__ == "__main__":
    make_cover_if_missing()
    print(f"Cover at {COVER_PATH}")
