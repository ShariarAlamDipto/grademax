"""
Correct the "PAPERS INCLUDED" list on the M1 / S1 / P4 yearwise back covers.

The supplied covers (data/workbook/M1 S1 P4 cover/) list sessions the books do
not contain and miss sessions they do -- e.g. P4 lists January 2019, which is
before P4 was first sat (October 2020); all three list June 2020, a cancelled
series; M1 lists 13 of its 20 papers. A back cover that disagrees with the book
is a misprint, so the list is rebuilt from the book's OWN paper list
(lib.yearwise_build.load_papers -- the same list the book is assembled from).

Only the list changes. Everything else on the artwork is untouched: the old
rows are REDACTED (glyphs and the dotted rules wholly inside a row removed;
the background grid, which runs past the row, is left alone), and the new rows
are set in the cover's own type -- IBM Plex Mono 8.5 number, Saira Condensed
SemiBold 12.5 session -- in its own colours, row pitch and dotted rule, all
read off the existing first row rather than typed in. The list keeps the
design's two columns unless they would run into the badge row below, then
uses three; the badge row's position is read off each cover.

The originals are not modified; corrected copies are written to
data/workbook/M1 S1 P4 cover/corrected/.

    python scripts/fix_yearwise_cover_lists.py
"""

from __future__ import annotations

import importlib
import math
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.yearwise_build import load_papers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COVERS = ROOT / "data" / "workbook" / "M1 S1 P4 cover"
OUT = COVERS / "corrected"
FONTS = Path(__file__).resolve().parent / "lib" / "fonts"
MONO = FONTS / "IBMPlexMono-Regular.ttf"
SAIRA = FONTS / "SairaCondensed-SemiBold.ttf"

SOURCES = {
    "m1": COVERS / "Front Pages M1 S1 P4" / "Mechanics_M1_WME01_YearWise_QP_Yellow.pdf",
    "s1": COVERS / "Front Pages M1 S1 P4" / "Statistics_S1_WST01_YearWise_QP_Lime.pdf",
    "p4": COVERS / "files" / "PureMaths_P4_WMA14_YearWise_QP.pdf",
}
MONTH = {"Jan": "JANUARY", "Jun": "JUNE", "Oct": "OCTOBER"}

ROW_NUMBER = re.compile(r"^\d{2}$")
COLUMN_RIGHT = 547.0      # the right edge the design's columns run to
RULE_DROP = 7.5           # dotted rule sits this far below the baseline
DOT, PITCH = 0.75, 2.0    # the rule is 0.75pt squares on a 2pt pitch


def sessions(unit: str) -> list[str]:
    plan = importlib.import_module(f"build_{unit}_yearwise_workbook").PLAN
    out = []
    for paper in load_papers(plan):
        month, year = paper.short.split()
        out.append(f"{MONTH[month]} {year}")
    return out


def old_rows(page: fitz.Page) -> list[dict]:
    """The existing list rows: number span, label span, their baseline."""
    rows = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            if (len(spans) >= 2 and spans[0]["font"].endswith("IBMPlexMono-Regular")
                    and ROW_NUMBER.match(spans[0]["text"].strip())):
                rows.append({"number": spans[0], "label": spans[1],
                             "x": spans[0]["origin"][0], "y": spans[0]["origin"][1]})
    return sorted(rows, key=lambda r: (r["x"], r["y"]))


def rgb(colour: int) -> tuple[float, float, float]:
    return ((colour >> 16 & 255) / 255, (colour >> 8 & 255) / 255, (colour & 255) / 255)


def dotted_rule(page: fitz.Page, x0: float, x1: float, y: float, colour) -> None:
    """The design's rule: a short lead tick, then 0.75pt squares every 2pt."""
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(x0 - 0.19, y, x0 + 1.31, y + DOT))
    x = x0 + 2.06
    while x + DOT <= x1:
        shape.draw_rect(fitz.Rect(x, y, x + DOT, y + DOT))
        x += PITCH
    shape.finish(color=None, fill=colour, width=0)
    shape.commit()


def fix(unit: str) -> Path:
    doc = fitz.open(SOURCES[unit])
    page = doc[1]
    rows = old_rows(page)
    if not rows:
        raise SystemExit(f"{unit}: no PAPERS INCLUDED rows found on the back cover")

    left_x = min(r["x"] for r in rows)
    first_y = min(r["y"] for r in rows)
    baselines = sorted({round(r["y"], 2) for r in rows})
    pitch = (baselines[-1] - baselines[0]) / (len(baselines) - 1)
    number_colour = rgb(rows[0]["number"]["color"])
    label_colour = rgb(rows[0]["label"]["color"])
    label_offset = rows[0]["label"]["origin"][0] - rows[0]["x"]
    # The rule under the first row gives its colour AND its drop below the
    # baseline -- 7.5pt on M1/S1, 8.25pt on P4, so it is measured, not assumed.
    first_rule = next(
        (d for d in page.get_drawings()
         if d["type"] == "f" and d["fill"] and d["rect"].width > 150
         and 5 < d["rect"].y0 - first_y < 11),
        None)
    rule_colour = first_rule["fill"] if first_rule else label_colour
    drop = first_rule["rect"].y0 - first_y if first_rule else RULE_DROP

    # The badge row ("FULL PAST PAPERS ...") is the floor the list must clear.
    floor = min((b["bbox"][1] for b in page.get_text("dict")["blocks"]
                 for line in b.get("lines", []) for sp in line["spans"]
                 if sp["text"].replace(" ", "").startswith("FULLPAST")),
                default=page.rect.height)
    max_rows = int((floor - 8 - drop - first_y) // pitch) + 1

    # Remove the old rows: each row's band, number to column edge, baseline
    # to just under its rule. Only what lies WHOLLY inside is removed.
    for r in rows:
        right = COLUMN_RIGHT if r["x"] > 200 else r["x"] + 236
        page.add_redact_annot(fitz.Rect(r["x"] - 1.5, r["y"] - 13.5,
                                        right, r["y"] + drop + 3.0), fill=False)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)

    wanted = sessions(unit)
    # Two columns as designed, three only if two would run into the badges.
    columns = 2 if math.ceil(len(wanted) / 2) <= max_rows else 3
    per_column = math.ceil(len(wanted) / columns)
    if per_column > max_rows:
        raise SystemExit(f"{unit}: {len(wanted)} sessions do not fit above the badges")
    span = COLUMN_RIGHT - left_x
    gap = 31.0
    width = (span - gap * (columns - 1)) / columns

    page.insert_font(fontname="plexmono", fontfile=str(MONO))
    page.insert_font(fontname="sairasb", fontfile=str(SAIRA))
    for index, label in enumerate(wanted):
        column, row = divmod(index, per_column)
        x = left_x + column * (width + gap)
        y = first_y + row * pitch
        page.insert_text((x, y), f"{index + 1:02d}", fontname="plexmono",
                         fontsize=8.5, color=number_colour)
        page.insert_text((x + label_offset, y), f" {label}", fontname="sairasb",
                         fontsize=12.5, color=label_colour)
        dotted_rule(page, x, x + width, y + drop, rule_colour)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / SOURCES[unit].name
    doc.save(target, garbage=3, deflate=True)
    doc.close()

    # Read it back: the list must now be exactly the book's sessions, in order.
    check = old_rows(fitz.open(target)[1])
    got = [re.sub(r"\s+", " ", r["label"]["text"]).strip()
           for r in sorted(check, key=lambda r: int(r["number"]["text"]))]
    if got != wanted:
        raise SystemExit(f"{unit}: read-back list {got} != book {wanted}")
    print(f"{unit}: {len(wanted)} sessions in {columns} columns -> {target.name}")
    return target


def main() -> int:
    for unit in SOURCES:
        fix(unit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
