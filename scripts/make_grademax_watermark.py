"""
Make the GradeMax-edition watermark: "MAXIMIZE YOUR GRADES / WITH / GRADEMAX".

Every chapterwise and yearwise book ships in two editions that differ only in
the watermark (user, 2026-10-09): the students' edition keeps the series mark
"ACING MATHEMATICS / WITH / SHARIAR ALAM DIPTO" (FINAL WATERMARK.png), and the
edition sold on GradeMax carries this one.

It is set in the SAME lockup as the series mark -- same canvas, rule, faces,
cap heights, colours, letter-spacing and centres -- by the measured method in
make_physics_watermark.py, which this reuses rather than repeats. That script's
self-check (re-render the original wording and compare it with the original
artwork) runs here too, so a drifted font cannot slip through.

    python scripts/make_grademax_watermark.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_physics_watermark as lockup  # noqa: E402

TARGET = lockup.ART / "GRADEMAX WATERMARK.png"
LINES = (
    ("ACING MATHEMATICS", "MAXIMIZE YOUR GRADES", lockup.BOLD),
    ("WITH", "WITH", lockup.WIDE),
    ("SHARIAR ALAM DIPTO", "GRADEMAX", lockup.REGULAR),
)


def main() -> int:
    lockup.LINES = LINES
    source = Image.open(lockup.SOURCE).convert("RGBA")
    bands = lockup.ink_bands(np.array(source)[:, :, 3])
    if len(bands) != 4:
        print(f"expected 4 ink bands (rule + 3 lines), found {len(bands)}")
        return 1

    rebuilt, _ = lockup.compose(source, bands, 0)
    a = Image.fromarray(((np.array(source)[:, :, 3] > 128) * 255).astype("uint8"))
    b = Image.fromarray(((np.array(rebuilt)[:, :, 3] > 128) * 255).astype("uint8"))
    near_b = np.array(b.filter(ImageFilter.MaxFilter(7))) > 0
    near_a = np.array(a.filter(ImageFilter.MaxFilter(7))) > 0
    ink_a, ink_b = np.array(a) > 0, np.array(b) > 0
    match = min((ink_a & near_b).sum() / ink_a.sum(), (ink_b & near_a).sum() / ink_b.sum())
    print(f"re-rendered original vs original artwork: {match:.1%} of ink within 3px")
    if match < 0.95:
        print("  too different -- the font or spacing does not match; not writing")
        return 1

    mark, notes = lockup.compose(source, bands, 1)
    # Hold the crop to the series lockup's extent (see make_physics_watermark),
    # so the type prints at the series size wherever the new title fits inside it.
    left, right = min(b[2] for b in bands), max(b[3] for b in bands)
    top, bottom = bands[0][0], bands[-1][1]
    for x, y in ((left, top), (right, bottom)):
        if mark.getpixel((x, y))[3] == 0:
            mark.putpixel((x, y), (255, 255, 255, 1))
    for note in notes:
        print(f"  {note}")
    mark.save(TARGET)
    print(f"written: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
