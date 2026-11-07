#!/usr/bin/env python3
"""Shop images: each book's ORIGINAL cover, shown as a photographed paperback.

The reference (CoverIns/*.jpg) is a product shot: a paperback lying on a soft
backdrop whose colour matches the cover, with a soft shadow to the lower left.
The cover artwork is not redrawn. Each listing's original cover
(R2 store/<slug>/cover.jpg) is placed as-is on a backdrop taken from that
cover's own main colour, with the shadow, spine fold and page edge that make
it read as a physical book.

These are SHOP images only (store_products.cover_image_url). The printed
books and their cover files are not touched.

    python -X utf8 scripts/design_store_mockup_covers.py
    python -X utf8 scripts/design_store_mockup_covers.py --only wph11-yearwise-2026

Output: output/store_covers_mockup/<slug>.jpg plus contact_sheet.jpg.
"""
from __future__ import annotations

import argparse
import colorsys
import io
import os
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

from store_cover_targets import ROOT, load_targets

OUT = ROOT / "output/store_covers_mockup"
ORIGINALS = ROOT / "output/store_covers_original"
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")

W, H = 1240, 1754          # final image, the store card's A-series ratio
BOOK_W = 820               # the book's width on the backdrop (about 2/3, like the reference)


def original_cover(slug: str) -> Image.Image:
    """The listing's original cover, downloaded once and kept in output/."""
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    path = ORIGINALS / f"{slug}.jpg"
    if not path.exists():
        r = requests.get(f"{R2_PUBLIC_URL}/store/{slug}/cover.jpg", timeout=60)
        r.raise_for_status()
        Image.open(io.BytesIO(r.content)).verify()
        path.write_bytes(r.content)
    return Image.open(path).convert("RGB")


def main_colour(cover: Image.Image) -> tuple[float, float, float]:
    """The cover's dominant colour: the most common hue bucket, weighted to saturated pixels."""
    px = np.asarray(cover.resize((120, 170)), dtype=np.float32).reshape(-1, 3) / 255
    hls = np.array([colorsys.rgb_to_hls(*p) for p in px])
    weight = hls[:, 2] * (1 - np.abs(hls[:, 1] - 0.5) * 1.6).clip(0.05, 1)
    buckets = (hls[:, 0] * 24).astype(int) % 24
    best = np.bincount(buckets, weights=weight, minlength=24).argmax()
    chosen = buckets == best
    hue = float(np.median(hls[chosen, 0])) if chosen.any() else 0.0
    sat = float(np.average(hls[chosen, 2], weights=weight[chosen])) if chosen.any() else 0.0
    light = float(np.average(hls[:, 1]))
    return hue, light, sat


def backdrop_colour(cover: Image.Image) -> tuple[int, int, int]:
    """A softer, greyed tone of the cover's colour, like the reference's sage wall."""
    hue, light, sat = main_colour(cover)
    if sat < 0.12:                       # a mostly neutral cover: a warm grey backdrop
        return (178, 174, 166)
    target_l = 0.30 if light < 0.32 else 0.56
    r, g, b = colorsys.hls_to_rgb(hue, target_l, min(sat * 0.55, 0.32))
    return int(r * 255), int(g * 255), int(b * 255)


def backdrop(colour: tuple[int, int, int]) -> Image.Image:
    """Flat colour with a gentle vignette and a faint paper grain, so it reads as a surface."""
    base = np.ones((H, W, 3), np.float32) * np.array(colour, np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt(((xx - W * 0.55) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
    base *= (1.04 - dist * 0.22)[..., None]
    rng = np.random.default_rng(7)
    base += rng.normal(0, 2.2, (H, W, 1))
    return Image.fromarray(base.clip(0, 255).astype(np.uint8))


def as_paperback(cover: Image.Image) -> Image.Image:
    """The cover at book size with a spine fold on the left and a lit edge on the right."""
    book_h = round(BOOK_W * cover.height / cover.width)
    book = cover.resize((BOOK_W, book_h), Image.LANCZOS)
    shade = np.zeros((book_h, BOOK_W), np.float32)
    x = np.arange(BOOK_W, dtype=np.float32)
    fold = 26
    shade[:, :fold] = (0.20 * (1 - x[:fold] / fold))[None, :]      # spine fold shadow
    shade[:, fold:fold + 3] = -0.06                                   # crease highlight
    arr = np.asarray(book, np.float32)
    arr = arr * (1 - shade.clip(0, 1)[..., None]) + 255 * (-shade.clip(-1, 0))[..., None]
    arr[:, -2:] = arr[:, -2:] * 0.7 + 255 * 0.3        # faint lit page edge on the right
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


def render(slug: str) -> Image.Image:
    cover = original_cover(slug)
    img = backdrop(backdrop_colour(cover))
    book = as_paperback(cover)
    x0 = (W - BOOK_W) // 2
    y0 = (H - book.height) // 2 - 10

    # Two shadows, light from the upper right as in the reference:
    # a wide soft one and a tight contact one along the lower-left edges.
    for spread, offset, strength in ((48, (-26, 34), 0.42), (10, (-6, 8), 0.38)):
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rectangle(
            (x0 + offset[0], y0 + offset[1], x0 + BOOK_W + offset[0] - 6, y0 + book.height + offset[1]),
            fill=int(255 * strength))
        mask = mask.filter(ImageFilter.GaussianBlur(spread))
        img.paste(Image.new("RGB", img.size, (20, 20, 18)), (0, 0), mask)

    img.paste(book, (x0, y0))
    return img


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
    if not R2_PUBLIC_URL:
        raise SystemExit("NEXT_PUBLIC_R2_PUBLIC_URL missing from .env.local")
    OUT.mkdir(parents=True, exist_ok=True)
    books = [b for b in load_targets() if not args.only or b["slug"] in args.only]
    paths = []
    for b in books:
        path = OUT / f"{b['slug']}.jpg"
        render(b["slug"]).save(path, quality=90, optimize=True, progressive=True)
        paths.append(path)
        print(f"{b['slug']:32} {path.stat().st_size // 1024} KB")
    if len(paths) > 1:
        contact_sheet(paths)
    print(f"{len(paths)} covers in {OUT}")


if __name__ == "__main__":
    main()
