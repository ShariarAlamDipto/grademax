#!/usr/bin/env python3
"""Render the store's book-cover images in the CoverIns reference style.

The reference (CoverIns/*.jpg) is a product shot: a cream paperback on a soft
backdrop of the same hue. Most of the cover is a single coloured block whose
lower-left edge sweeps away in a curve. The title is set in spaced Garamond
capitals, a small figure sits where the curve meets the block, an italic
subtitle is at the lower left and the author at the lower right.

These are SHOP images only (store_products.cover_image_url). The printed
books' own covers are not touched.

    python -X utf8 scripts/design_store_mockup_covers.py            # all target books
    python -X utf8 scripts/design_store_mockup_covers.py --only wph11-yearwise-2026

Output: output/store_covers_mockup/<slug>.jpg plus contact_sheet.jpg. The
book list comes from the live catalogue (read-only), see store_cover_targets.py.
"""
from __future__ import annotations

import argparse
import colorsys
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from store_cover_targets import ROOT, load_targets

OUT = ROOT / "output/store_covers_mockup"
FONTS = Path("C:/Windows/Fonts")
SERIF = FONTS / "GARA.TTF"
SERIF_ITALIC = FONTS / "GARAIT.TTF"

SS = 2                        # supersampling factor for smooth edges
W, H = 1240, 1754             # final image (A-series ratio, matches the store card)
BOOK = (205, 175, 1035, 1555)  # book face in final pixels: x0, y0, x1, y1
PAPER = (236, 230, 216)
INK = (52, 50, 46)
AUTHOR = "SHARIAR ALAM DIPTO"

# Block colour per subject. Deep, slightly muted tones like the reference green.
PALETTE = {
    "maths": (88, 125, 44),
    "further": (46, 106, 104),
    "mechanics": (160, 84, 46),
    "statistics": (62, 79, 138),
    "decision": (110, 64, 108),
    "physics": (36, 73, 112),
    "chemistry": (136, 48, 58),
    "biology": (44, 104, 84),
    "humanbio": (124, 84, 50),
    "accounting": (44, 88, 120),
    "business": (164, 104, 44),
    "economics": (120, 60, 82),
    "english": (92, 76, 122),
    "ict": (40, 108, 130),
    "computing": (58, 72, 92),
}


def palette_key(title: str, code: str) -> str:
    t = title.lower()
    for word, key in (("further pure", "further"), ("mechanics", "mechanics"),
                      ("statistics", "statistics"), ("decision", "decision"),
                      ("human biology", "humanbio"), ("physics", "physics"),
                      ("chemistry", "chemistry"), ("biology", "biology"),
                      ("accounting", "accounting"), ("business", "business"),
                      ("economics", "economics"), ("english", "english"),
                      ("ict", "ict"), ("computer", "computing")):
        if word in t:
            return key
    return "maths"


def backdrop_of(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """A pale, greyed version of the block colour, like the reference's sage wall."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    r, g, b = colorsys.hls_to_rgb(h, 0.60, min(s, 0.30))
    return int(r * 255), int(g * 255), int(b * 255)


def font(path: Path, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), int(size * SS))


def tracked_width(f: ImageFont.FreeTypeFont, text: str, tracking: float) -> float:
    return sum(f.getlength(ch) for ch in text) + tracking * SS * max(len(text) - 1, 0)


def draw_tracked(d: ImageDraw.ImageDraw, x: float, y: float, text: str,
                 f: ImageFont.FreeTypeFont, fill, tracking: float) -> None:
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking * SS


def wrap_title(words: list[str], size: float, max_w: float, tracking: float) -> list[str]:
    f = font(SERIF, size)
    lines: list[str] = []
    for word in words:
        trial = f"{lines[-1]} {word}" if lines else word
        short = len(word) <= 3 or len(lines[-1] if lines else "") <= 3
        if lines and short and tracked_width(f, trial, tracking) <= max_w:
            lines[-1] = trial          # glue short words ("A", "B", "P1") onto the line before
        else:
            lines.append(word)
    return lines


def fit_title(title: str, max_w: float, max_h: float) -> tuple[list[str], float]:
    words = title.upper().split()
    for size in range(76, 38, -2):
        tracking = size * 0.16
        lines = wrap_title(words, size, max_w, tracking)
        f = font(SERIF, size)
        widest = max(tracked_width(f, ln, tracking) for ln in lines)
        if widest <= max_w and len(lines) * size * 1.55 <= max_h:
            return lines, size
    return wrap_title(words, 38, max_w, 38 * 0.16), 38


def split_title(full: str) -> tuple[str, str | None]:
    """'Computer Science (Paper 1) — Yearwise ...' -> ('Computer Science', 'Paper 1')."""
    name = full.split("—")[0].strip()
    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    name = re.sub(r",\s*Part \d$", "", name)
    return name, None


def subtitle_lines(book: dict, extra: str | None) -> list[str]:
    title = book["title"]
    sub = book.get("subtitle") or ""
    if "Yearwise" in title:
        kind = "Yearwise question booklet"
    elif "Chapterwise" in title:
        kind = "Chapterwise workbook"
    else:
        kind = "Practice book"
    if extra and extra.lower().startswith("parts"):
        extra = "in two volumes"
    first = f"{kind}, {extra.lower()}" if extra and extra.lower() in ("higher", "foundation") \
        else f"{kind} {extra}" if extra and extra.startswith("in ") \
        else f"{kind}, {extra}" if extra else kind
    parts = [p.strip() for p in sub.split("·")]
    second = parts[-1] if len(parts) > 1 else ""
    if second.lower().startswith("complete specification") or not second or "volumes" in second:
        second = "Complete specification"
    second = second.replace(" - ", " – ").replace("October/November", "Oct/Nov")
    return [first, second]


def block_shape(x0: float, y0: float, x1: float, y1: float, sweep_x: float, lift: float) -> list:
    """Block outline: square top, flat bottom on the right, curved sweep on the left."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (sweep_x, y1)]
    # Cubic from (sweep_x, y1) back to (x0, y1 - lift): an S-curve like the reference.
    p0, p3 = (sweep_x, y1), (x0, y1 - lift)
    c1 = (sweep_x - (sweep_x - x0) * 0.55, y1)
    c2 = (x0 + (sweep_x - x0) * 0.45, y1 - lift)
    for i in range(1, 41):
        t = i / 40
        u = 1 - t
        pts.append((u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1]))
    return pts


def draw_reader(d: ImageDraw.ImageDraw, bx: float, by: float, s: float, ink) -> None:
    """A small seated student reading on a bench; (bx, by) is the bench's foot line."""
    k = s * SS
    seat_y = by - 22 * k
    # bench: seat plank, back legs
    d.rounded_rectangle((bx - 60 * k, seat_y - 4 * k, bx + 60 * k, seat_y + 2 * k), radius=2 * k, fill=ink)
    for lx in (-52, 50):
        d.rectangle((bx + lx * k, seat_y, bx + (lx + 4) * k, by), fill=ink)
    # person (seated, facing right, book held up)
    hip = (bx - 8 * k, seat_y - 4 * k)
    d.polygon([(hip[0] - 9 * k, hip[1]), (hip[0] + 9 * k, hip[1]),
               (hip[0] + 7 * k, hip[1] - 34 * k), (hip[0] - 9 * k, hip[1] - 32 * k)], fill=ink)  # torso
    d.ellipse((hip[0] - 7 * k, hip[1] - 50 * k, hip[0] + 7 * k, hip[1] - 36 * k), fill=ink)        # head
    d.polygon([(hip[0] - 6 * k, hip[1] - 2 * k), (hip[0] + 26 * k, hip[1] - 2 * k),
               (hip[0] + 26 * k, hip[1] + 4 * k), (hip[0] - 6 * k, hip[1] + 4 * k)], fill=ink)   # thigh
    d.polygon([(hip[0] + 21 * k, hip[1]), (hip[0] + 27 * k, hip[1]),
               (hip[0] + 28 * k, by - 1 * k), (hip[0] + 22 * k, by - 1 * k)], fill=ink)          # shin
    d.rectangle((hip[0] + 22 * k, by - 3 * k, hip[0] + 33 * k, by), fill=ink)                     # foot
    d.line([(hip[0] + 2 * k, hip[1] - 28 * k), (hip[0] + 15 * k, hip[1] - 16 * k),
            (hip[0] + 20 * k, hip[1] - 25 * k)], fill=ink, width=int(5 * k), joint="curve")      # arm
    d.polygon([(hip[0] + 16 * k, hip[1] - 22 * k), (hip[0] + 25 * k, hip[1] - 36 * k),
               (hip[0] + 29 * k, hip[1] - 33 * k), (hip[0] + 21 * k, hip[1] - 19 * k)],
              fill=(250, 248, 240))                                                               # open book
    # a soft ground shadow under the bench
    d.ellipse((bx - 64 * k, by - 2 * k, bx + 64 * k, by + 5 * k), fill=(205, 198, 182))


def render(book: dict) -> Image.Image:
    name, extra = split_title(book["title"])
    colour = PALETTE[palette_key(name, book.get("subject_code") or "")]
    back = backdrop_of(colour)

    img = Image.new("RGB", (W * SS, H * SS), back)
    bx0, by0, bx1, by1 = (v * SS for v in BOOK)

    # backdrop: gentle vignette, then the book's shadow (light from the upper right)
    shade = Image.new("L", img.size, 0)
    sd = ImageDraw.Draw(shade)
    sd.rectangle((bx0 - 38 * SS, by0 + 30 * SS, bx1 - 8 * SS, by1 + 46 * SS), fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(34 * SS))
    img.paste(Image.new("RGB", img.size, tuple(int(c * 0.62) for c in back)), (0, 0), shade)

    d = ImageDraw.Draw(img)
    d.rectangle((bx0, by0, bx1, by1), fill=PAPER)
    # spine fold and a faint page edge, so it reads as a paperback
    d.rectangle((bx0, by0, bx0 + 7 * SS, by1), fill=tuple(c - 14 for c in PAPER))
    d.line([(bx0 + 7 * SS, by0), (bx0 + 7 * SS, by1)], fill=tuple(c - 26 for c in PAPER), width=SS)

    bw, bh = bx1 - bx0, by1 - by0
    kx0, ky0 = bx0 + bw * 0.072, by0 + bh * 0.03
    kx1, ky1 = bx1 - bw * 0.072, by0 + bh * 0.62
    sweep_x = kx0 + (kx1 - kx0) * 0.38
    d.polygon(block_shape(kx0, ky0, kx1, ky1, sweep_x, bh * 0.065), fill=colour)

    # small tracked label at the top of the block
    level = "EDEXCEL IAL" if (book.get("subject_code") or "").startswith("W") else "EDEXCEL IGCSE"
    label = f"{level}  ·  {(book.get('subject_code') or '').replace('4CP1', '4CP0')}"
    lf = font(SERIF, 21)
    lw = tracked_width(lf, label, 5)
    draw_tracked(d, (kx0 + kx1) / 2 - lw / 2, ky0 + 62 * SS, label, lf,
                 tuple(int(p * 0.82 + c * 0.18) for p, c in zip(PAPER, colour)), 5)

    # title, centred in the upper part of the block
    max_w = (kx1 - kx0) - 110 * SS
    lines, size = fit_title(name, max_w, (ky1 - ky0) * 0.52)
    tf = font(SERIF, size)
    tracking = size * 0.16
    line_h = size * 1.55 * SS
    top = ky0 + (ky1 - ky0) * 0.40 - line_h * len(lines) / 2
    for i, ln in enumerate(lines):
        lw = tracked_width(tf, ln, tracking)
        draw_tracked(d, (kx0 + kx1) / 2 - lw / 2, top + i * line_h, ln, tf, PAPER, tracking)

    # the reader sits where the curve meets the flat edge, like the reference's bench
    draw_reader(d, sweep_x + 18 * SS, ky1 + 1 * SS, 1.45, (34, 34, 32))

    # lower text: italic subtitle left, author right
    sf = font(SERIF_ITALIC, 33)
    sy = by0 + bh * 0.80
    sub = subtitle_lines(book, extra)
    for i, ln in enumerate(sub):
        d.text((kx0, sy + i * 44 * SS), ln, font=sf, fill=INK)
    af = font(SERIF, 21)
    aw = tracked_width(af, AUTHOR, 3.2)
    widest = max(sf.getlength(ln) for ln in sub)
    # beside the subtitle when there is room (as in the reference), otherwise beneath it
    ay = sy + 50 * SS if kx0 + widest + 40 * SS < kx1 - aw else sy + 120 * SS
    draw_tracked(d, kx1 - aw, ay, AUTHOR, af, INK, 3.2)
    mark = "GRADEMAX  ·  TRI AXIS EDUCATION"
    mf = font(SERIF, 15)
    mw = tracked_width(mf, mark, 3)
    draw_tracked(d, (bx0 + bx1) / 2 - mw / 2, by1 - 48 * SS, mark, mf, (120, 114, 102), 3)

    return img.resize((W, H), Image.LANCZOS)


def contact_sheet(paths: list[Path]) -> None:
    cols, tw = 8, 240
    th = int(tw * H / W)
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), "white")
    for i, p in enumerate(paths):
        sheet.paste(Image.open(p).resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    sheet.save(OUT / "contact_sheet.jpg", quality=85)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", help="slugs to render")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    books = [b for b in load_targets() if not args.only or b["slug"] in args.only]
    paths = []
    for b in books:
        path = OUT / f"{b['slug']}.jpg"
        render(b).save(path, quality=90, optimize=True, progressive=True)
        paths.append(path)
        print(f"{b['slug']:32} {path.stat().st_size // 1024} KB")
    if len(paths) > 1:
        contact_sheet(paths)
    print(f"{len(paths)} covers in {OUT}")


if __name__ == "__main__":
    main()
