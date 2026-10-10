"""
Put the covers and the watermark on the Further Pure Maths book, then audit it.

Two volumes are finished, because two volumes are bound: the question book and
its mark schemes. Both get the same front and back cover -- they are one series,
and a mark scheme volume that arrives at the printer without a cover comes back
with a plain card one.

    python scripts/finalize_fpm_workbook_print.py            # paged edition
    python scripts/finalize_fpm_workbook_print.py trimmed
    python scripts/finalize_fpm_workbook_print.py verbatim

The paged edition is the default because it is the only one built from the
current builder -- it carries the Formula Sheet, the chapter openers and the
diary. The other two are kept reachable so an older edition can be finished
without editing this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import workbook_total_band
from lib.workbook_finish import assemble, load_watermark, locked, report, verify

ROOT = Path(__file__).resolve().parent.parent
PRINT = ROOT / "data" / "workbook" / "fpm" / "print"
FINAL = PRINT / "final"

ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
COVER = ART / "Further Pure Maths Front and Back cover" / "Fav 4.pdf"
WATERMARK = ART / "Final Water Mark" / "FINAL WATERMARK.png"

SUFFIX = {"paged": "_Paged", "verbatim": "_Verbatim", "trimmed": ""}

# Text that must be present on each cover, used to prove the front cover is not
# bound on the back. Taken from the artwork's own text layer.
COVER_TOKENS = ("CHAPTERWISE WORKBOOK", "TEN CHAPTERS,")

VOLUMES = (
    ("GradeMax_FPM_Workbook{suffix}.pdf",
     "Further_Pure_Mathematics_Workbook_PRINT.pdf",
     "Further Pure Mathematics 4PM1 - Question book",
     True),
    ("GradeMax_FPM_Workbook_MarkSchemes{suffix}.pdf",
     "Further_Pure_Mathematics_MarkSchemes_PRINT.pdf",
     "Further Pure Mathematics 4PM1 - Mark scheme book",
     False),
)


def band_repair(edition: str):
    """
    The question book's stale "(Total for Question N)" bands, or nothing.

    Only the question book carries the bands, and only an edition with an index
    can be repaired -- the index is where the workbook's own number comes from.
    Pass --no-repair to leave the sheets exactly as the builder made them.
    """
    if "--no-repair" in sys.argv:
        return None, []
    index_path = PRINT / f"print_index{SUFFIX[edition].lower()}.json"
    if not index_path.is_file():
        return None, []
    questions = json.loads(index_path.read_text(encoding="utf-8"))["questions"]

    fixes: list = []

    def run(interior):
        fixes.extend(workbook_total_band.repair(interior, questions))
        return fixes

    return run, questions


def main() -> int:
    edition = sys.argv[1] if len(sys.argv) > 1 else "paged"
    if edition not in SUFFIX:
        print(f"unknown edition {edition!r}; expected one of {sorted(SUFFIX)}")
        return 2
    suffix = SUFFIX[edition]

    for path in (COVER, WATERMARK):
        if not path.is_file():
            print(f"missing artwork: {path}")
            return 1

    mark = load_watermark(WATERMARK)
    problems = 0

    for source_name, out_name, title, repairable in VOLUMES:
        source = PRINT / source_name.format(suffix=suffix)
        if not source.is_file():
            print(f"\nnot built, skipped: {source}")
            problems += 1
            continue

        out = FINAL / out_name
        if locked(out):
            print(f"\n  SKIPPED, file is open elsewhere: {out}")
            print("  close it in your PDF reader and re-run.")
            problems += 1
            continue

        repair, questions = band_repair(edition) if repairable else (None, [])
        stats = assemble(source, COVER, WATERMARK, out, repair=repair)
        repaired = {fix.page for fix in stats["repairs"]}
        found = verify(out, source, COVER, mark, COVER_TOKENS, repaired=repaired)

        # Re-read the finished file: no band anywhere may still contradict the
        # workbook, including on pages the repair pass never touched.
        if questions:
            import fitz
            book = fitz.open(out)
            found += workbook_total_band.verify(book, questions)
            book.close()

        problems += report(f"{title}  ({edition})", stats, found)
        print(f"  written           : {out}")

    print(f"\n{'=' * 74}\n  TOTAL PROBLEMS: {problems}\n{'=' * 74}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
