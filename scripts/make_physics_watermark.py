"""
Make the Physics book's watermark: "ACING PHYSICS / WITH / GRADEMAX".

The series watermark (FINAL WATERMARK.png, used by the Further Pure Maths and
Maths B books) reads "ACING MATHEMATICS / WITH / SHARIAR ALAM DIPTO". The
Physics book carries its own wording in the SAME lockup, so the books still
read as one series: same canvas (5184 x 1072, transparent), same rule, same
type (Saira Condensed SemiBold title, Arial "WITH", Saira Condensed Regular
name line), same
cap heights, colours, letter-spacing and centre line.

Every one of those numbers is MEASURED from the original artwork, not typed in:
each line's ink band gives its cap height, colour and width, and the
letter-spacing is solved by re-setting the original words until they reproduce
the original widths. The same settings then set the new words. The check at the
end re-renders the original lockup and compares it to the original PNG, which
is what shows the font and spacing really match.

    python scripts/make_physics_watermark.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover" / "Final Water Mark"
SOURCE = ART / "FINAL WATERMARK.png"
TARGET = ART / "PHYSICS WATERMARK.png"
FONTS = Path(__file__).resolve().parent / "lib" / "fonts"
BOLD = FONTS / "SairaCondensed-SemiBold.ttf"
REGULAR = FONTS / "SairaCondensed-Regular.ttf"
# The small grey "WITH" is NOT the condensed face: it is a normal-width sans.
# Scored against the original's ink, Arial matched 96% and the next best
# (Corbel) 90%, so it is Arial (or a metric twin such as Arimo).
WIDE = Path("C:/Windows/Fonts/arial.ttf")

# (original words, new words, font) for each text line, top to bottom.
LINES = (
    ("ACING MATHEMATICS", "ACING PHYSICS", BOLD),
    ("WITH", "WITH", WIDE),
    ("SHARIAR ALAM DIPTO", "GRADEMAX", REGULAR),
)


def ink_bands(alpha: np.ndarray) -> list[tuple[int, int, int, int]]:
    """(y0, y1, x0, x1) of each horizontal band of ink, top to bottom."""
    rows = np.where(alpha.max(1) > 40)[0]
    bands, start, prev = [], rows[0], rows[0]
    for row in rows[1:]:
        if row > prev + 3:
            bands.append((start, prev))
            start = row
        prev = row
    bands.append((start, prev))
    out = []
    for y0, y1 in bands:
        cols = np.where(alpha[y0:y1 + 1].max(0) > 40)[0]
        out.append((int(y0), int(y1), int(cols[0]), int(cols[-1])))
    return out


def set_line(text: str, font_path: Path, cap: int, tracking: float):
    """Render one line; returns (RGBA mask image, ink width, ink height)."""
    size = cap * 1.5
    for _ in range(30):  # size the font so the ink height equals `cap`
        font = ImageFont.truetype(str(font_path), int(round(size)))
        mask = render(text, font, tracking)
        box = mask.getbbox()
        height = box[3] - box[1]
        if abs(height - cap) <= 1:
            break
        size *= cap / height
    box = mask.getbbox()
    return mask.crop(box), box[2] - box[0], box[3] - box[1]


def render(text: str, font, tracking: float) -> Image.Image:
    width = int(sum(font.getlength(c) for c in text) + tracking * len(text) + 200)
    mask = Image.new("L", (width, int(font.size * 2)), 0)
    draw = ImageDraw.Draw(mask)
    x = 50.0
    for char in text:
        draw.text((x, 20), char, font=font, fill=255)
        x += font.getlength(char) + tracking
    return mask


def solve_tracking(text: str, font_path: Path, cap: int, width: int) -> float:
    """Letter-spacing (px) that makes `text` exactly `width` wide."""
    low, high = -40.0, 400.0
    for _ in range(40):
        middle = (low + high) / 2
        _, got, _ = set_line(text, font_path, cap, middle)
        low, high = (middle, high) if got < width else (low, middle)
    return (low + high) / 2


def compose(source: Image.Image, bands, words_index: int) -> tuple[Image.Image, list[str]]:
    """Rebuild the lockup with LINES[*][words_index] wording."""
    canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
    pixels = np.array(source)
    notes = []

    rule = bands[0]
    rule_colour = tuple(int(v) for v in pixels[rule[0]:rule[1] + 1, rule[2]:rule[3] + 1, :3]
                        [pixels[rule[0]:rule[1] + 1, rule[2]:rule[3] + 1, 3] > 200].mean(0))

    text_lines = []
    for (old, new, font), (y0, y1, x0, x1) in zip(LINES, bands[1:]):
        cap, width = y1 - y0 + 1, x1 - x0 + 1
        region = pixels[y0:y1 + 1, x0:x1 + 1]
        colour = tuple(int(v) for v in region[:, :, :3][region[:, :, 3] > 200].mean(0))
        tracking = solve_tracking(old, font, cap, width)
        mask, got, _ = set_line(old if words_index == 0 else new, font, cap, tracking)
        text_lines.append((mask, y0, colour, (x0 + x1) / 2))
        notes.append(f"{(old if words_index == 0 else new)!r}: cap {cap}px, tracking "
                     f"{tracking:.1f}px, width {got}px, colour {colour}")

    # The rule spans the title in the original (896 of 1728px, centred); keep
    # its own measured length -- it is a fixed element of the lockup.
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((rule[2], rule[0], rule[3], rule[1]), fill=rule_colour + (255,))

    # Each line on ITS OWN measured centre: in the original they do not share
    # one (the title sits ~12px left of the rule's centre).
    for mask, top, colour, centre in text_lines:
        left = int(round(centre - mask.width / 2))
        solid = Image.new("RGBA", mask.size, colour + (255,))
        canvas.paste(solid, (left, top), mask)
    return canvas, notes


def main() -> int:
    source = Image.open(SOURCE).convert("RGBA")
    bands = ink_bands(np.array(source)[:, :, 3])
    if len(bands) != 4:
        print(f"expected 4 ink bands (rule + 3 lines), found {len(bands)}")
        return 1

    # Check: rebuild the ORIGINAL wording and compare it with the original.
    # Strict per-pixel overlap is the wrong measure for thin anti-aliased
    # strokes (a sub-pixel shift halves it), so each image's ink must lie
    # within 3px of the other's -- both ways, so missing or extra strokes fail.
    rebuilt, _ = compose(source, bands, 0)
    a = Image.fromarray(((np.array(source)[:, :, 3] > 128) * 255).astype("uint8"))
    b = Image.fromarray(((np.array(rebuilt)[:, :, 3] > 128) * 255).astype("uint8"))
    near_b = np.array(b.filter(ImageFilter.MaxFilter(7))) > 0
    near_a = np.array(a.filter(ImageFilter.MaxFilter(7))) > 0
    ink_a, ink_b = np.array(a) > 0, np.array(b) > 0
    match = min((ink_a & near_b).sum() / ink_a.sum(), (ink_b & near_a).sum() / ink_b.sum())
    print(f"re-rendered original vs original artwork: {match:.1%} of ink within 3px")
    # 95%: measured per line on the final settings -- rule 100%, name 97%,
    # "WITH" 96%, title 95%. The title's residue is stroke-edge weight
    # (anti-aliasing), confirmed by eye on a side-by-side render, not shape.
    if match < 0.95:
        print("  too different -- the font or spacing does not match; not writing")
        return 1

    physics, notes = compose(source, bands, 1)

    # Keep the SAME TYPE SIZE as the series. lib.workbook_finish crops the
    # artwork to its ink and scales that to a fixed share of the page width,
    # so a narrower title ("ACING PHYSICS" is 1226px against 1728px) would be
    # printed ~1.4x larger. Two alpha=1 pixels at the original lockup's ink
    # extremes hold the crop to the original's extent; at alpha 1/255 after
    # the 10% lightening they print as nothing.
    left = min(b[2] for b in bands)
    right = max(b[3] for b in bands)
    top, bottom = bands[0][0], bands[-1][1]
    for x, y in ((left, top), (right, bottom)):
        if physics.getpixel((x, y))[3] == 0:
            physics.putpixel((x, y), (255, 255, 255, 1))
    for note in notes:
        print(f"  {note}")
    physics.save(TARGET)
    print(f"written: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
