"""
Finish the 2018-2026 MATHS yearwise books: cover on, and the "Acing Mathematics
with Shariar Alam Dipto" watermark on every interior sheet -- the same artwork,
policy and code as the FPM / Maths B workbooks and the M1/S1/P4 yearwise books
(`workbook_finish.assemble` + `verify`), so the whole maths shelf matches.

The watermark is a maths brand, so only maths books are finished with it
(4MB1, 4PM1, IAL P1-P4); the science books keep plain interiors.

Writes data/yearwise_all/books/<book>/final/GradeMax_<CODE>_Yearwise_Vol<n>_<Kind>.pdf
"""

from __future__ import annotations

from pathlib import Path

import fitz

from .workbook_finish import assemble, load_watermark, locked, report, verify
from .yearwise_all_catalogue import ROOT, WORK
from .yearwise_all_layout import SUB
from .yearwise_finish import WATERMARK


def _compact(path: Path) -> None:
    """
    assemble() saves plainly (a deliberate choice for the 180MB chapterwise
    books). These books place each source sheet through its own one-page copy,
    so a plain save repeats fonts per sheet: a 14MB interior became 127MB.
    Re-saved with duplicate objects merged and streams deflated -- and verify()
    then runs on the COMPACTED file, so nothing ships that was not checked.
    """
    tmp = path.with_name(path.stem + ".tmp.pdf")
    with fitz.open(path) as doc:
        doc.save(tmp, garbage=3, deflate=True)
    tmp.replace(path)


def finish(book: str, code: str, subject: str) -> int:
    folder = WORK / "books" / book
    final = folder / "final"
    if not WATERMARK.exists():
        print(f"watermark artwork not found: {WATERMARK}")
        return 1
    mark = load_watermark(WATERMARK)
    final.mkdir(parents=True, exist_ok=True)
    problems = 0
    interiors = sorted(folder.glob(f"{code}_Yearwise_Vol*_interior.pdf"))
    if not interiors:
        print(f"{book}: nothing built yet")
        return 1
    for interior in interiors:
        stem = interior.name.replace("_interior.pdf", "")
        cover = folder / f"{stem}_cover.pdf"
        out = final / f"GradeMax_{stem}.pdf"
        if locked(out):
            print(f"{out.name} is open in a reader -- skipped")
            problems += 1
            continue
        stats = assemble(interior, cover, WATERMARK, out)
        _compact(out)
        found = verify(out, interior, cover, mark, (SUB.upper(), subject))
        problems += report(out.name, stats, found)
    print(f"\n{book}: {'all volumes finished in ' + str(final.relative_to(ROOT)) if not problems else str(problems) + ' problems'}")
    return 1 if problems else 0
