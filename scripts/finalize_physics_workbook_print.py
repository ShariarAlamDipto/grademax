"""
Put the covers and the watermark on the Physics book, then audit it.

Port of finalize_mathsb_workbook_print.py: the question book and its mark
scheme book, the series watermark lockup -- worded "ACING PHYSICS WITH GRADEMAX" -- at
the same size and weight as Further Pure Maths and Maths B, the stale "(Total for Question N = M marks)" bands
redrawn to the workbook's own numbering, and every finished file read back by
lib.workbook_finish.verify.

THE COVER
---------
There is no Physics cover artwork yet. Until there is, a plain typographic
two-page cover is generated (front: title, subject code, edition; back: the
GradeMax line) so the file is complete and printable. To use real artwork,
put a 2-page PDF (front, back) at COVER_ART; it is used automatically and must
carry COVER_TOKENS somewhere in its text, or the audit reports it.

    python scripts/finalize_physics_workbook_print.py            # paged edition
    python scripts/finalize_physics_workbook_print.py trimmed
    python scripts/finalize_physics_workbook_print.py paged --part all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import workbook_total_band  # noqa: E402
from lib.workbook_finish import (  # noqa: E402
    PAGE_HEIGHT, PAGE_WIDTH, assemble, load_watermark, locked, report, verify,
)

ROOT = Path(__file__).resolve().parent.parent
PRINT = ROOT / "data" / "workbook" / "physics" / "print"
FINAL = PRINT / "final"
COVERS = PRINT / "covers"
ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
COVER_ART = ART / "Physics Front and Back Cover" / "Physics_Cover.pdf"
# "ACING PHYSICS / WITH / GRADEMAX" -- the series lockup with Physics wording,
# made by scripts/make_physics_watermark.py (same type, size and weight).
WATERMARK = ART / "Final Water Mark" / "PHYSICS WATERMARK.png"

SUFFIX = {"trimmed": "", "paged": "_Paged", "verbatim": "_Verbatim"}
COVER_TOKENS = ("CHAPTERWISE WORKBOOK", "GradeMax")
PART_LABEL = {1: "PART ONE", 2: "PART TWO"}

VOLUMES = (
    ("GradeMax_Physics_Workbook{suffix}.pdf",
     "Physics_Workbook_PRINT{part}.pdf",
     "Physics 4PH1 - Question book", True, "QUESTIONS"),
    ("GradeMax_Physics_Workbook_MarkSchemes{suffix}.pdf",
     "Physics_MarkSchemes_PRINT{part}.pdf",
     "Physics 4PH1 - Mark scheme book", False, "MARK SCHEMES"),
)

INK = (0.07, 0.11, 0.20)
ACCENT = (0.10, 0.36, 0.55)
MUTED = (0.40, 0.44, 0.50)


def part_suffix(part: int | None) -> str:
    return "" if part is None else f"_Part{part}"


def generated_cover(volume: str, part: int | None) -> Path:
    """A plain two-page cover, used only while no artwork exists."""
    COVERS.mkdir(parents=True, exist_ok=True)
    target = COVERS / f"Physics_Cover_{volume.replace(' ', '_')}{part_suffix(part)}.pdf"
    doc = fitz.open()

    front = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    front.draw_rect(front.rect, color=None, fill=INK)
    front.draw_rect(fitz.Rect(0, 520, PAGE_WIDTH, 528), color=None, fill=ACCENT)
    left = 56
    front.insert_text((left, 150), "GradeMax", fontname="hebo", fontsize=22, color=(1, 1, 1))
    front.insert_text((left, 250), "Edexcel International GCSE", fontname="helv",
                      fontsize=15, color=(0.85, 0.88, 0.93))
    front.insert_text((left, 312), "Physics", fontname="hebo", fontsize=54, color=(1, 1, 1))
    front.insert_text((left, 346), "4PH1  ·  Past papers 2018 – 2023", fontname="helv",
                      fontsize=14, color=(0.85, 0.88, 0.93))
    front.insert_text((left, 440), "CHAPTERWISE WORKBOOK", fontname="hebo",
                      fontsize=20, color=(1, 1, 1))
    front.insert_text((left, 470), volume, fontname="helv", fontsize=14,
                      color=(0.85, 0.88, 0.93))
    if part is not None:
        front.insert_text((left, 498), PART_LABEL[part], fontname="hebo", fontsize=14,
                          color=(1, 1, 1))
    front.insert_text((left, 600), "8 chapters  ·  30 sections  ·  every question "
                      "with its mark scheme", fontname="helv", fontsize=11,
                      color=(0.85, 0.88, 0.93))

    back = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    back.draw_rect(back.rect, color=None, fill=INK)
    back.insert_text((left, PAGE_HEIGHT - 80), "GradeMax  ·  grademax.me", fontname="hebo",
                     fontsize=13, color=(1, 1, 1))

    # Shipped the way real cover artwork is: one image per page. The shared
    # audit (lib.workbook_finish.verify) checks a cover is exactly that, and
    # reads its title from text -- so the words go back on as an INVISIBLE
    # text layer (render mode 3) over the picture.
    flat = fitz.open()
    for page in doc:
        words = page.get_text("words")
        sheet = flat.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        sheet.insert_image(sheet.rect, pixmap=page.get_pixmap(dpi=300))
        for x0, _, _, y1, word, *_ in words:
            sheet.insert_text((x0, y1 - 2), word, fontsize=9, render_mode=3)
    doc.close()
    flat.save(target, deflate=True)
    flat.close()
    return target


def cover_for(volume: str, part: int | None) -> Path:
    if COVER_ART.is_file():
        return COVER_ART
    return generated_cover(volume, part)


def band_repair(edition: str, part: int | None):
    """Redraw stale question-total bands against this volume's own index."""
    if "--no-repair" in sys.argv:
        return None, []
    index_path = PRINT / f"print_index{SUFFIX[edition].lower()}{part_suffix(part).lower()}.json"
    if not index_path.is_file():
        return None, []
    questions = json.loads(index_path.read_text(encoding="utf-8"))["questions"]
    fixes: list = []

    def run(interior):
        fixes.extend(workbook_total_band.repair(interior, questions))
        return fixes

    return run, questions


def finalize(edition: str, part: int | None) -> int:
    suffix = SUFFIX[edition]
    mark = load_watermark(WATERMARK)
    problems = 0

    for source_name, out_name, title, repairable, volume in VOLUMES:
        source = PRINT / source_name.format(suffix=suffix + part_suffix(part))
        if not source.is_file():
            print(f"\nnot built, skipped: {source}")
            problems += 1
            continue
        out = FINAL / out_name.format(part=part_suffix(part))
        if locked(out):
            print(f"\n  SKIPPED, file is open elsewhere: {out}")
            problems += 1
            continue

        cover = cover_for(volume, part)
        repair, questions = band_repair(edition, part) if repairable else (None, [])
        stats = assemble(source, cover, WATERMARK, out, repair=repair)
        repaired = {fix.page for fix in stats["repairs"]}
        found = verify(out, source, cover, mark, COVER_TOKENS, repaired=repaired)
        if questions:
            book = fitz.open(out)
            found += workbook_total_band.verify(book, questions)
            book.close()
        label = title + (f" - Part {part}" if part else "")
        problems += report(f"{label}  ({edition})", stats, found)
        print(f"  cover             : {cover.name}"
              f"{'' if cover == COVER_ART else '  (generated -- no artwork yet)'}")
        print(f"  written           : {out}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("edition", nargs="?", default="paged", choices=sorted(SUFFIX))
    parser.add_argument("--part", choices=("1", "2", "all"))
    parser.add_argument("--no-repair", action="store_true")
    args = parser.parse_args()

    if not WATERMARK.is_file():
        print(f"missing watermark artwork: {WATERMARK}")
        return 1

    parts: list[int | None] = [None]
    if args.part == "all":
        parts = [1, 2]
    elif args.part:
        parts = [int(args.part)]

    problems = sum(finalize(args.edition, part) for part in parts)
    print(f"\n{'=' * 74}\n  TOTAL PROBLEMS: {problems}\n{'=' * 74}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
