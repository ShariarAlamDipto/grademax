"""
Put the "Acing Mathematics with Shariar Alam Dipto" watermark on the maths
companion books -- worked solutions and teacher's notes -- which were rendered
straight to their final PDFs and so never went through the workbook finisher.

Same artwork, size, ink and placement as every other maths book
(`workbook_finish.load_watermark` + `stamp`: 55% of the page wide, centred,
10% ink, drawn UNDER the page). Every page but the first (the book's own title
page) is marked. The original is backed up first; the result is compacted and
then re-read to prove every page carries the mark.

    python -X utf8 scripts/watermark_maths_companions.py            # dry run
    python -X utf8 scripts/watermark_maths_companions.py --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.workbook_finish import load_watermark, locked, stamp  # noqa: E402
from lib.yearwise_finish import WATERMARK  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOKS = [
    "data/workbook/fpm/print/final/Further_Pure_Mathematics_Worked_Solutions.pdf",
    "data/workbook/fpm/print/final/Further_Pure_Mathematics_Worked_Solutions_Complete.pdf",
    "data/workbook/fpm/print/final/Further_Pure_Mathematics_Teachers_Notes.pdf",
    "data/workbook/mathsb/print/final/Mathematics_B_Worked_Solutions_Part1.pdf",
    "data/workbook/mathsb/print/final/Mathematics_B_Worked_Solutions_Part2.pdf",
    "data/workbook/mathsb/print/final/Mathematics_B_Teachers_Notes.pdf",
    "data/workbook/p4/print/final/Pure_Mathematics_4_Teachers_Notes.pdf",
]


def carries_mark(page: fitz.Page) -> bool:
    """The mark: an image ~55% of the page wide, centred."""
    w = page.rect.width
    for info in page.get_images(full=True):
        for r in page.get_image_rects(info[0]):
            if abs(r.width - 0.55 * w) < 0.05 * w and abs((r.x0 + r.x1) / 2 - w / 2) < 20:
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mark = load_watermark(WATERMARK)
    backup = ROOT / "data" / "backups" / f"watermark_companions_{dt.date.today():%Y%m%d}"
    bad = 0
    for rel in BOOKS:
        path = ROOT / rel
        if not path.exists():
            print(f"  missing   {rel}")
            bad += 1
            continue
        with fitz.open(path) as doc:
            already = sum(carries_mark(doc[i]) for i in range(1, doc.page_count))
            pages = doc.page_count
        if already == pages - 1:
            print(f"  done      {rel} ({pages}pp already marked)")
            continue
        if not args.apply:
            print(f"  would     {rel}: mark pages 2-{pages}")
            continue
        if locked(path):
            print(f"  LOCKED    {rel} is open in a reader -- skipped")
            bad += 1
            continue
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / path.name)
        doc = fitz.open(path)
        xref = 0
        for i in range(1, doc.page_count):
            xref = stamp(doc[i], mark, xref)
        tmp = path.with_name(path.stem + ".tmp.pdf")
        doc.save(tmp, garbage=3, deflate=True)
        doc.close()
        tmp.replace(path)
        with fitz.open(path) as doc:
            marked = sum(carries_mark(doc[i]) for i in range(1, doc.page_count))
            title_clean = not carries_mark(doc[0])
            ok = marked == doc.page_count - 1 and title_clean
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'}      {rel}: {marked}/{pages - 1} pages marked, "
              f"title page {'clean' if title_clean else 'MARKED'}, {path.stat().st_size // 1_000_000} MB")
    if args.apply and not bad:
        print(f"\nbackups: {backup.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
