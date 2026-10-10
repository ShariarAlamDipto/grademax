"""
The two editions every chapterwise and yearwise book ships in.

User, 2026-10-09: the same book is sold through two channels, and each carries
its own watermark. Nothing else differs -- same interior, same covers.

    GradeMax   sold on the GradeMax store   "MAXIMIZE YOUR GRADES / WITH / GRADEMAX"
    Students   sold to the user's students  "ACING MATHEMATICS / WITH / SHARIAR ALAM DIPTO"

The GradeMax artwork is generated in the series lockup by
scripts/make_grademax_watermark.py. A finisher writes one file per edition,
suffixed with the edition's name, so the two cannot be mixed up at the printer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover" / "Final Water Mark"


@dataclass(frozen=True)
class Edition:
    name: str        # file suffix and report label
    artwork: Path
    wording: str


EDITIONS: tuple[Edition, ...] = (
    Edition("GradeMax", ART / "GRADEMAX WATERMARK.png", "Maximize your grades with GradeMax"),
    Edition("Students", ART / "FINAL WATERMARK.png", "Acing Mathematics with Shariar Alam Dipto"),
)


def edition_path(path: Path, edition: Edition) -> Path:
    """`.../M1_Workbook_PRINT.pdf` -> `.../M1_Workbook_PRINT_GradeMax.pdf`."""
    return path.with_name(f"{path.stem}_{edition.name}{path.suffix}")


def missing_artwork() -> list[Path]:
    return [e.artwork for e in EDITIONS if not e.artwork.is_file()]
