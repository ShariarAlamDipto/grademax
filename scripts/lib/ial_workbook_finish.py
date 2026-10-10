"""
Covers, watermark and the final audit for the IAL chapterwise books (P1, P2,
S1, M1) -- generalised from finalize_physics_workbook_print.py. Each unit has a
thin finalize_<unit>_workbook_print.py that calls `finalize_unit`.

The watermark is the maths series artwork ("Acing Mathematics with Shariar Alam
Dipto", FINAL WATERMARK.png) at the series' size and weight. Until a unit has
cover artwork, a typographic cover is generated; put a 2-page PDF (front, back)
at the unit's COVER_ART path to use real artwork instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

from . import workbook_continued_header, workbook_total_band
from .watermark_editions import EDITIONS, edition_path, missing_artwork
from .workbook_finish import (
    PAGE_HEIGHT, PAGE_WIDTH, assemble, load_watermark, locked, report, verify,
)

ROOT = Path(__file__).resolve().parents[2]
# Set per unit by finalize_unit().
PRINT = FINAL = COVERS = ROOT
TOKEN = NAME = CODE = "UNSET"
ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
COVER_ART = ART  # set per unit by finalize_unit()
# The maths series watermark: "Acing Mathematics with Shariar Alam Dipto".
WATERMARK = ART / "Final Water Mark" / "FINAL WATERMARK.png"

SUFFIX = {"trimmed": "", "paged": "_Paged", "verbatim": "_Verbatim"}
COVER_TOKENS = ("CHAPTERWISE WORKBOOK", "GradeMax")
PART_LABEL = {1: "PART ONE", 2: "PART TWO"}

def volumes():
    return (
        (f"GradeMax_{TOKEN}_Workbook{{suffix}}.pdf", f"{TOKEN}_Workbook_PRINT{{part}}.pdf",
         f"{NAME} {CODE} - Question book", True, "QUESTIONS"),
        (f"GradeMax_{TOKEN}_Workbook_MarkSchemes{{suffix}}.pdf",
         f"{TOKEN}_MarkSchemes_PRINT{{part}}.pdf",
         f"{NAME} {CODE} - Mark scheme book", False, "MARK SCHEMES"),
    )


INK = (0.07, 0.11, 0.20)
ACCENT = (0.10, 0.36, 0.55)
MUTED = (0.40, 0.44, 0.50)


def part_suffix(part: int | None) -> str:
    return "" if part is None else f"_Part{part}"


def generated_cover(volume: str, part: int | None) -> Path:
    """A plain two-page cover, used only while no artwork exists."""
    COVERS.mkdir(parents=True, exist_ok=True)
    target = COVERS / f"{TOKEN}_Cover_{volume.replace(' ', '_')}{part_suffix(part)}.pdf"
    doc = fitz.open()

    front = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    front.draw_rect(front.rect, color=None, fill=INK)
    front.draw_rect(fitz.Rect(0, 520, PAGE_WIDTH, 528), color=None, fill=ACCENT)
    left = 56
    front.insert_text((left, 150), "GradeMax", fontname="hebo", fontsize=22, color=(1, 1, 1))
    front.insert_text((left, 250), "Edexcel International Advanced Level", fontname="helv",
                      fontsize=15, color=(0.85, 0.88, 0.93))
    front.insert_text((left, 312), NAME, fontname="hebo", fontsize=40, color=(1, 1, 1))
    front.insert_text((left, 346), f"{CODE}  ·  Past papers 2019 – 2026", fontname="helv",
                      fontsize=14, color=(0.85, 0.88, 0.93))
    front.insert_text((left, 440), "CHAPTERWISE WORKBOOK", fontname="hebo",
                      fontsize=20, color=(1, 1, 1))
    front.insert_text((left, 470), volume, fontname="helv", fontsize=14,
                      color=(0.85, 0.88, 0.93))
    if part is not None:
        front.insert_text((left, 498), PART_LABEL[part], fontname="hebo", fontsize=14,
                          color=(1, 1, 1))
    front.insert_text((left, 600), "Every question sorted by chapter, with its mark scheme",
                      fontname="helv", fontsize=11, color=(0.85, 0.88, 0.93))

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
        headers = workbook_continued_header.repair(interior, questions)
        HEADER_PAGES.clear()
        HEADER_PAGES.update(fix.page for fix in headers)
        print(f"  continued headers : {len(headers)} renumbered to match the workbook")
        return fixes

    return run, questions


# Pages whose "Question N continued" header the last repair rewrote. They are
# legitimate text changes, so verify() must not count them as unexplained.
HEADER_PAGES: set[int] = set()


def finalize(edition: str, part: int | None) -> int:
    return sum(finalize_one(edition, part, mark_edition) for mark_edition in EDITIONS)


def finalize_one(edition: str, part: int | None, mark_edition) -> int:
    """One watermark edition (lib/watermark_editions) of every volume."""
    suffix = SUFFIX[edition]
    mark = load_watermark(mark_edition.artwork)
    problems = 0

    for source_name, out_name, title, repairable, volume in volumes():
        source = PRINT / source_name.format(suffix=suffix + part_suffix(part))
        if not source.is_file():
            print(f"\nnot built, skipped: {source}")
            problems += 1
            continue
        out = edition_path(FINAL / out_name.format(part=part_suffix(part)), mark_edition)
        if locked(out):
            print(f"\n  SKIPPED, file is open elsewhere: {out}")
            problems += 1
            continue

        cover = cover_for(volume, part)
        repair, questions = band_repair(edition, part) if repairable else (None, [])
        stats = assemble(source, cover, mark_edition.artwork, out, repair=repair)
        repaired = {fix.page for fix in stats["repairs"]} | (HEADER_PAGES if repair else set())
        found = verify(out, source, cover, mark, COVER_TOKENS, repaired=repaired)
        if questions:
            book = fitz.open(out)
            found += workbook_total_band.verify(book, questions)
            found += workbook_continued_header.verify(book, questions)
            book.close()
        label = title + (f" - Part {part}" if part else "")
        problems += report(f"{label}  ({edition}, {mark_edition.name} edition)", stats, found)
        print(f"  cover             : {cover.name}"
              f"{'' if cover == COVER_ART else '  (generated -- no artwork yet)'}")
        print(f"  written           : {out}")
    return problems


def finalize_unit(unit: str, code: str, name: str, cover_art: Path | None = None) -> int:
    global PRINT, FINAL, COVERS, TOKEN, NAME, CODE, COVER_ART
    PRINT = ROOT / "data" / "workbook" / unit / "print"
    FINAL, COVERS = PRINT / "final", PRINT / "covers"
    TOKEN, NAME, CODE = unit.upper(), name, code
    COVER_ART = cover_art or (ART / f"{unit.upper()} Front and Back Cover"
                              / f"{unit.upper()}_Cover.pdf")

    parser = argparse.ArgumentParser()
    parser.add_argument("edition", nargs="?", default="paged", choices=sorted(SUFFIX))
    parser.add_argument("--part", choices=("1", "2", "all"))
    parser.add_argument("--no-repair", action="store_true")
    args = parser.parse_args()
    missing = missing_artwork()
    if missing:
        print(f"missing watermark artwork: {missing}")
        return 1
    parts: list[int | None] = [None]
    if args.part == "all":
        parts = [1, 2]
    elif args.part:
        parts = [int(args.part)]
    problems = sum(finalize(args.edition, part) for part in parts)
    print(f"\n{'=' * 74}\n  TOTAL PROBLEMS: {problems}\n{'=' * 74}")
    return 0 if problems == 0 else 1
