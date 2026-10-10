"""
Put the covers and the watermark on a yearwise workbook, then audit it.

Both volumes of a unit are finished, because both are bound: a mark scheme book
sent to a printer without a cover comes back with a plain card one.

The watermark is the same artwork and the same policy as the FPM and Maths B
books -- 55% of the page wide, centred, 10% ink, drawn UNDER the page -- and it
is applied by the same code, so the whole shelf matches. Drawing it underneath
only works because a reprinted exam sheet marks the paper where there is ink
and nowhere else; if a future edition starts painting its own white ground the
mark will disappear, and this is the first place to look.
"""

from __future__ import annotations

from pathlib import Path

from .watermark_editions import EDITIONS, edition_path, missing_artwork
from .workbook_finish import assemble, load_watermark, locked, report, verify

ROOT = Path(__file__).resolve().parents[2]

WATERMARK = (Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
             / "Final Water Mark" / "FINAL WATERMARK.png")

# Text the finisher looks for to prove the front cover is not bound on the back.
# The first is on every cover this series generates; the second is the unit's
# own name, supplied per unit.
COVER_TOKEN = "YEARWISE PRACTICE WORKBOOK"


# Text on the supplied "Year-wise Question Paper" artwork (front, back), used
# to prove a supplied cover is bound the right way round.
SUPPLIED_COVER_TOKENS = ("YEAR-WISE QUESTION PAPER", "EVERY PAPER, YEAR BY YEAR.")


def finish(slug: str, token: str, name: str, only: str | None = None,
           question_cover: Path | None = None) -> int:
    """
    `question_cover` is supplied artwork (2 pages, front + back) for the
    QUESTION book. The supplied covers say "Year-wise Question Paper", so the
    mark scheme book keeps its generated cover rather than wear that title.
    """
    build = ROOT / "data" / "workbook" / f"{slug}_yearwise"
    final = build / "final"
    prefix = f"{token}_Yearwise"

    missing = missing_artwork()
    if missing:
        print(f"watermark artwork not found: {missing}")
        return 1
    final.mkdir(parents=True, exist_ok=True)
    problems = 0

    plan = {
        "questions": (f"{prefix}_Questions_interior.pdf",
                      f"{prefix}_Questions_cover.pdf",
                      f"GradeMax_{token}_Yearwise_Workbook.pdf",
                      f"{name} yearwise workbook - question book"),
        "markschemes": (f"{prefix}_MarkSchemes_interior.pdf",
                        f"{prefix}_MarkSchemes_cover.pdf",
                        f"GradeMax_{token}_Yearwise_Workbook_MarkSchemes.pdf",
                        f"{name} yearwise workbook - mark scheme book"),
    }

    for kind, (interior, cover, out_name, title) in plan.items():
        if only and kind != only:
            continue
        interior_path, cover_path = build / interior, build / cover
        tokens = (COVER_TOKEN, name)
        if kind == "questions" and question_cover is not None:
            if not question_cover.exists():
                print(f"{title}: supplied cover not found: {question_cover}")
                problems += 1
                continue
            cover_path, tokens = question_cover, SUPPLIED_COVER_TOKENS
        if not interior_path.exists():
            print(f"{title}: not built yet ({interior})")
            problems += 1
            continue
        # One file per edition (lib/watermark_editions): identical but for the mark.
        for edition in EDITIONS:
            out_path = edition_path(final / out_name, edition)
            # Asked per file, not per run: a reader left open on one file
            # should not stop the others being finished.
            if locked(out_path):
                print(f"{title}: {out_path.name} is open in a reader -- skipped")
                problems += 1
                continue
            mark = load_watermark(edition.artwork)
            stats = assemble(interior_path, cover_path, edition.artwork, out_path)
            found = verify(out_path, interior_path, cover_path, mark, tokens)
            problems += report(f"{title} [{edition.name} edition]", stats, found)
            print(f"  written           : {out_path.name}")

    print()
    if problems:
        print(f"{problems} problems -- not ready to send")
        return 1
    print(f"both volumes, {len(EDITIONS)} editions each, written to {final.relative_to(ROOT)}")
    return 0
