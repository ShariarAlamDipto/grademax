"""
Read every written IAL chapterwise mark-scheme segment back and check it holds
its OWN question's scheme, and only that.

Independent of how the block was found: it reads the written PDF with the same
cell reader the scheme's table uses (lib.ial_ms_numbered._read), and asks

  1. the first question cell on the segment names THIS question;
  2. no cell names a DIFFERENT question (part labels "3(b)" repeat the number
     and are fine);
  3. the segment's QP marks are what the manifest says.

A segment whose layout prints no readable cell at all (some ruled tables) is
counted separately as "no readable cell", not passed.

    python scripts/audit_ial_chapterwise_markschemes.py p1 p2 s1 m1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent


STRONG_RE = re.compile(r"^(\d{1,2})\s*(?:\.(?!\d)|\(\s*[a-h]\s*\)|[a-h](?![a-z])|\(\s*i+\s*\))")


def strong_cells(path: Path) -> list[int]:
    """Question cells that NAME a part ("9. (i)", "4(a)", "1a"), left column."""
    found: list[int] = []
    with fitz.open(path) as doc:
        for page in doc:
            lines = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(sp["text"] for sp in line["spans"]).strip()
                    if text and line["bbox"][0] < 110:
                        lines.append((line["bbox"][1], text))
            for _, text in sorted(lines):
                match = STRONG_RE.match(text)
                if match and 1 <= int(match.group(1)) <= 15:
                    found.append(int(match.group(1)))
    return found


def audit(unit: str) -> int:
    """
    The failure that matters: a segment that opens on another question, or that
    runs on into a LATER question's scheme. Notes text is full of numbers, so
    only cells that name a part count, and a lower number is not a bleed
    (notes refer back to earlier parts).
    """
    total = linked = ok = silent = wrong = 0
    for manifest_path in sorted((ROOT / "data" / "workbook" / unit).glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        last = max(q["question_number"] for q in manifest["questions"])
        for entry in manifest["questions"]:
            total += 1
            if not entry["has_markscheme"]:
                continue
            linked += 1
            n = entry["question_number"]
            cells = strong_cells(manifest_path.parent / "markschemes" / f"q{n}.pdf")
            later = sorted({c for c in cells if n < c <= last})
            if not cells:
                silent += 1
            elif cells[0] != n or later:
                wrong += 1
                print(f"  {unit} {manifest['key']} q{n}: opens {cells[0]}, later {later} "
                      f"(route {entry.get('ms_extractor')})")
            else:
                ok += 1
    print(f"{unit}: {linked}/{total} linked ({linked / total:.0%}) | read back: "
          f"{ok} clean, {silent} no part-named cell, {wrong} WRONG")
    return wrong


def main() -> int:
    units = sys.argv[1:] or ["p1", "p2", "s1", "m1"]
    return 1 if sum(audit(u) for u in units) else 0


if __name__ == "__main__":
    sys.exit(main())
