"""Parse processed-paper folder names for both subject naming conventions.

Physics folders: 2024_May-Jun_P1, 2024_May-Jun_P1R, 2025_Oct-Nov_P2, 2012_Jan_P2
FPM folders:     2024_Jun_1P,    2024_Jun_1RP,    2025_Nov_2P,     2012_Jan_2P
"""
from __future__ import annotations
import re
from dataclasses import dataclass

_SUMMER = {"may-jun", "jun", "june", "may", "summer"}
_AUTUMN = {"oct-nov", "nov", "november", "oct", "october", "autumn"}
_WINTER = {"jan", "january", "winter"}


def normalize_session(raw: str) -> str:
    s = raw.strip().lower()
    if s in _SUMMER:
        return "summer"
    if s in _AUTUMN:
        return "autumn"
    if s in _WINTER:
        return "winter"
    return s


@dataclass(frozen=True)
class PaperFolder:
    folder: str
    year: int
    session: str          # normalized: summer | autumn | winter
    session_raw: str
    paper: str            # "1" | "2"
    variant: str          # "" | "R" (retake)

    @property
    def is_retake(self) -> bool:
        return self.variant == "R"

    @property
    def paper_id(self) -> str:
        return self.paper

    @property
    def label(self) -> str:
        r = "R" if self.is_retake else ""
        return f"{self.year} {self.session_raw} P{self.paper}{r}"


def parse_folder(name: str) -> PaperFolder | None:
    """Return PaperFolder or None if the name is not a recognizable paper folder."""
    parts = name.split("_")
    if len(parts) < 3:
        return None
    if not re.fullmatch(r"\d{4}", parts[0]):
        return None
    year = int(parts[0])
    session_raw = parts[1]
    paper_token = parts[-1]

    digit = re.search(r"\d", paper_token)
    if not digit:
        return None
    paper = digit.group(0)
    variant = "R" if "R" in paper_token.upper() else ""

    return PaperFolder(
        folder=name,
        year=year,
        session=normalize_session(session_raw),
        session_raw=session_raw,
        paper=paper,
        variant=variant,
    )
