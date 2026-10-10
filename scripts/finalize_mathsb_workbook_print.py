"""
Put the covers and the watermark on the Maths B book, then audit it.

Same two volumes as Further Pure Maths -- the question book and its mark
schemes -- and the same watermark artwork, at the same size and the same
weight, so the two books read as one series on the shelf.

    python scripts/finalize_mathsb_workbook_print.py            # paged edition
    python scripts/finalize_mathsb_workbook_print.py trimmed
    python scripts/finalize_mathsb_workbook_print.py paged --part 1
    python scripts/finalize_mathsb_workbook_print.py paged --part all

The default is the PAGED edition, to match Further Pure Maths. The trimmed
edition reduces each question to its printed content and hands it a measured
block of ruled space, which reads as a workbook; the paged edition reproduces
the board's own sheets, which reads as an exam paper -- the furniture, the
spacing and the "do not write in this area" margins all survive. That is the
thing worth having in a book someone revises from, so it is what gets built by
default. Pass `trimmed` to go back to the shorter edition.

THE TWO-PART SET
----------------
The paged volumes run to 933 and 1,205 sheets, past what a spiral binding will
take, so they are issued as Part 1 (chapters 1-5) and Part 2 (chapters 6-11,
opening at Geometry). Each part is a book in its own right and gets its own
front and back cover, with the front carrying the part on the CHAPTERWISE
WORKBOOK line in that line's own type -- see lib/workbook_cover_part.py, which
also explains why the label is not simply drawn on.

`--part 1` or `--part 2` finalises one volume; `--part all` finalises whichever
of the four exist. With no `--part`, the single undivided volume is finalised,
which is what the argument-free command has always done.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import workbook_cover_part, workbook_total_band
from lib.workbook_finish import assemble, load_watermark, locked, report, verify

ROOT = Path(__file__).resolve().parent.parent
PRINT = ROOT / "data" / "workbook" / "mathsb" / "print"
FINAL = PRINT / "final"
COVERS = PRINT / "covers"

ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
COVER = ART / "Maths B Front and Back Cover" / "MathsB_Composed_Indigo.pdf"
WATERMARK = ART / "Final Water Mark" / "FINAL WATERMARK.png"

SUFFIX = {"trimmed": "", "paged": "_Paged", "verbatim": "_Verbatim"}

COVER_TOKENS = ("CHAPTERWISE WORKBOOK", "SIX STRANDS,")

VOLUMES = (
    ("GradeMax_MathsB_Workbook{suffix}.pdf",
     "Mathematics_B_Workbook_PRINT{part}.pdf",
     "Mathematics B 4MB1 - Question book",
     True),
    ("GradeMax_MathsB_Workbook_MarkSchemes{suffix}.pdf",
     "Mathematics_B_MarkSchemes_PRINT{part}.pdf",
     "Mathematics B 4MB1 - Mark scheme book",
     False),
)


def band_repair(edition: str, part: int | None):
    """
    The question book's stale "(Total for Question N)" bands, or nothing.

    Maths B renumbers questions exactly as Further Pure Maths does, so it
    inherits the same defect: the number beside the question is patched to the
    workbook's own, the board's "(Total for Question N is M marks)" band at the
    foot of it is not. Pass --no-repair to leave the sheets as the builder made
    them.

    Each part has its OWN index, because each part renumbers its own pages from
    one; repairing Part 2 against the whole book's index would match bands to
    the wrong questions entirely.
    """
    if "--no-repair" in sys.argv:
        return None, []
    stem = f"print_index{SUFFIX[edition].lower()}{part_suffix(part).lower()}"
    index_path = PRINT / f"{stem}.json"
    if not index_path.is_file():
        return None, []
    questions = json.loads(index_path.read_text(encoding="utf-8"))["questions"]

    fixes: list = []

    def run(interior):
        fixes.extend(workbook_total_band.repair(interior, questions))
        return fixes

    return run, questions


def part_suffix(part: int | None) -> str:
    return "" if part is None else f"_Part{part}"


def cover_for(part: int | None) -> Path:
    """The artwork this volume goes out in, made once and reused."""
    if part is None:
        return COVER
    made = workbook_cover_part.part_cover(COVER, part, COVERS)
    problems = workbook_cover_part.verify(made, part)
    if problems:
        raise RuntimeError("part cover is wrong: " + "; ".join(problems))
    return made


def finalize(edition: str, part: int | None) -> int:
    """Finish both volumes of one part. Returns the problem count."""
    suffix = SUFFIX[edition]
    cover = cover_for(part)
    mark = load_watermark(WATERMARK)
    problems = 0

    for source_name, out_name, title, repairable in VOLUMES:
        source = PRINT / source_name.format(suffix=suffix + part_suffix(part))
        if not source.is_file():
            print(f"\nnot built, skipped: {source}")
            problems += 1
            continue

        out = FINAL / out_name.format(part=part_suffix(part))
        if locked(out):
            print(f"\n  SKIPPED, file is open elsewhere: {out}")
            print("  close it in your PDF reader and re-run.")
            problems += 1
            continue

        repair, questions = band_repair(edition, part) if repairable else (None, [])
        stats = assemble(source, cover, WATERMARK, out, repair=repair)
        repaired = {fix.page for fix in stats["repairs"]}
        found = verify(out, source, cover, mark, COVER_TOKENS, repaired=repaired)

        # Re-read the finished file: no band anywhere may still contradict the
        # workbook, including on pages the repair pass never touched.
        if questions:
            import fitz
            book = fitz.open(out)
            found += workbook_total_band.verify(book, questions)
            book.close()

        label = title + (f" - Part {part}" if part else "")
        problems += report(f"{label}  ({edition})", stats, found)
        print(f"  written           : {out}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("edition", nargs="?", default="paged", choices=sorted(SUFFIX))
    parser.add_argument("--part", choices=("1", "2", "all"),
                        help="finalise one volume of the two-part set, or both")
    parser.add_argument("--no-repair", action="store_true",
                        help="leave the board's question-total bands as built")
    args = parser.parse_args()

    parts: list[int | None] = [None]
    if args.part == "all":
        parts = [1, 2]
    elif args.part:
        parts = [int(args.part)]

    for path in (COVER, WATERMARK):
        if not path.is_file():
            print(f"missing artwork: {path}")
            return 1

    problems = sum(finalize(args.edition, part) for part in parts)
    print(f"\n{'=' * 74}\n  TOTAL PROBLEMS: {problems}\n{'=' * 74}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
