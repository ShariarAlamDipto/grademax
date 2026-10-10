"""
Write the print shop's handover sheet for the Maths B volumes, from the files.

Every number in PRINT_SPEC.md -- page counts, file sizes, which folios are soft,
which faces the RIP will substitute and on how many pages -- is measured out of
the finished PDFs rather than typed. The sheet was maintained by hand while
there was one pair of volumes; there are now four, and four volumes' worth of
copied figures is exactly the kind of thing that goes to a printer wrong.

    python scripts/write_mathsb_print_spec.py            # whatever is in final/
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz

from lib.workbook_print_audit import press_readiness

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "workbook" / "mathsb" / "print" / "final"
SPEC = FINAL / "PRINT_SPEC.md"

COVER_SHEETS = 1

# Every volume that may exist, in the order the printer should receive them.
VOLUMES = (
    ("Mathematics_B_Workbook_PRINT_Part1.pdf", "Questions, Part 1", "chapters 1–5"),
    ("Mathematics_B_MarkSchemes_PRINT_Part1.pdf", "Mark schemes, Part 1", "chapters 1–5"),
    ("Mathematics_B_Workbook_PRINT_Part2.pdf", "Questions, Part 2", "chapters 6–11"),
    ("Mathematics_B_MarkSchemes_PRINT_Part2.pdf", "Mark schemes, Part 2", "chapters 6–11"),
    ("Mathematics_B_Workbook_PRINT.pdf", "Questions, single volume", "chapters 1–11"),
    ("Mathematics_B_MarkSchemes_PRINT.pdf", "Mark schemes, single volume", "chapters 1–11"),
)


def measure(path: Path) -> dict:
    book = fitz.open(path)
    press = press_readiness(book, COVER_SHEETS)
    measured = {
        "pages": book.page_count,
        "mb": path.stat().st_size / 1_048_576,
        "press": press,
    }
    book.close()
    return measured


def soft_line(press: dict) -> str:
    """The folios that will print soft, or a statement that none will."""
    pages = sorted({p for band in press["soft"].values() for p in band})
    if not pages:
        return "none below 200 dpi"
    shown = ", ".join(str(p) for p in pages[:6])
    more = f" and {len(pages) - 6} more" if len(pages) > 6 else ""
    return f"{len(pages)} folio{'s' if len(pages) > 1 else ''} ({shown}{more})"


def font_line(press: dict) -> str:
    risky = press["risky"]
    if not risky:
        return "all embedded"
    return "; ".join(f"{name} on {len(pages)} pages"
                     for name, pages in sorted(risky.items(), key=lambda kv: -len(kv[1])))


def main() -> int:
    found = [(name, role, span, FINAL / name) for name, role, span in VOLUMES
             if (FINAL / name).is_file()]
    if not found:
        print(f"no finished volumes in {FINAL}")
        return 1

    # Once the two-part set exists it IS the run. The undivided volumes stay on
    # disk, so they have to be named and ruled out here rather than left in the
    # table for a print shop to guess at.
    parted = any("_Part" in name for name, *_ in found)
    superseded = [n for n, *_ in found if parted and "_Part" not in n]
    found = [row for row in found if not (parted and "_Part" not in row[0])]

    rows, detail = [], []
    for name, role, span, path in found:
        m = measure(path)
        press = m["press"]
        low, mid, high = press["dpi"] or (0, 0, 0)
        rows.append(f"| `{name}` | {role} | {span} | {m['pages']} | "
                    f"{m['mb']:.1f} MB |")
        detail.append(f"| `{name}` | {mid:.0f} dpi ({low:.0f}–{high:.0f}) | "
                      f"{soft_line(press)} | {font_line(press)} |")
        if len(press["sizes"]) != 1 or press["rotated"] or press["cropped"]:
            detail.append(f"| | **check**: sizes {press['sizes']}, "
                          f"{len(press['rotated'])} rotated, "
                          f"{len(press['cropped'])} cropbox mismatches | | |")

    aside = ""
    if superseded:
        aside = ("\n**Do not print** `" + "`, `".join(superseded) + "` — "
                 "the undivided edition of the same material, kept for reference "
                 "only. Printing it as well would duplicate the whole book.\n")

    text = f"""# Mathematics B (4MB1) — print specification

Measured from the delivered files on {date.today():%d %B %Y} by
`scripts/write_mathsb_print_spec.py`. Every figure below is read out of the PDF,
not transcribed.

Each file is final and self-contained: the covers are the first and last page of
the PDF itself, and every interior page is watermarked. Do not add a separate
cover file.

| File | Volume | Contents | Pages | Size |
|---|---|---|---|---|
{chr(10).join(rows)}

{aside}
{"The set is issued in TWO PARTS so each volume takes a spiral binding. Part 1 ends with chapter 5 (Matrices) and Part 2 opens at chapter 6 (Geometry). Each part is a complete book — its own covers, contents, summary-and-formulae section, page numbers from 1 and question index — so the two are bound and used independently. The mark scheme volumes split at the same chapter, so Part 1 mark schemes answer Part 1 questions." if parted else ""}

The volumes reproduce the board's own sheets at 1:1, so the exam furniture — the
ruled answer lines, the "do not write in this area" margins and the original
spacing — is intact. That is what the page count buys.

## Make-up

- **Page 1** is the front cover, **the last page** is the back cover. Both are
  full-colour; the front names the part.
- **Pages 2 to N-1** are the interior. Mono (black only) throughout — the
  interior contains no colour work.
- Interior page numbering starts at 1 on sheet 2, so the printed folio and the
  PDF page differ by one. The contents and the question index refer to the
  **printed** folio.
- Every page is 595 × 842 pt with no rotation and no CropBox/MediaBox
  discrepancy.

## The mark scheme volumes read sideways — this is intended

Edexcel sets the Maths B mark schemes in **landscape**, and most of the pages in
those volumes are landscape originals. They are placed turned a quarter turn on
portrait sheets, so the reader turns the book clockwise to read them. The book's
own footer and folio stay upright at the foot of the sheet.

Print them portrait like any other volume — the rotation is baked into the page
content, not a page-level rotation flag, so there is nothing for the RIP to
decide. Do **not** "correct" the orientation or set it to auto-rotate.

## Bleed

The covers are supplied **trimmed to A4 with no bleed**. If the press needs
bleed on the cover, ask for the artwork to be re-exported at 210 × 297 mm + 3 mm
— do not scale this file up to fake it, because that shrinks the interior text
block relative to the trim.

## Measured, per volume

| File | Image detail | Soft pages | Unembedded faces |
|---|---|---|---|
{chr(10).join(detail)}

Two things to check before the run, both inherited from Edexcel's own published
PDFs rather than introduced here:

1. **Fonts.** Where a face is listed as unembedded above, the RIP will
   substitute. Arial Narrow is used for working inside the mark scheme tables at
   about 8 pt and regular Arial sets **wider**, so a substitution can overflow a
   cell — please confirm the face is resident, or proof those folios.

2. **Scan detail.** The soft folios listed above were scanned at that resolution
   originally and cannot be recovered. It is expected, not a fault in the file.

## File size

If the shop's upload portal rejects a volume, send it on physical media rather
than re-compressing — re-compression is what turns a 279 dpi scan into a soft
one.

## Watermark

A light grey brand mark sits centred on every interior page at 10% ink, 55% of
the page width, printed UNDER the question so the text and the ruled lines stay
crisp over it. It is intended to be faint. If it does not appear on the proof,
the RIP has dropped a soft mask — say so rather than printing the run.
"""

    SPEC.write_text(text.replace("\n\n\n", "\n\n"), encoding="utf-8")
    print(f"  {SPEC}")
    for name, role, span, _ in found:
        print(f"    {role:<28} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
