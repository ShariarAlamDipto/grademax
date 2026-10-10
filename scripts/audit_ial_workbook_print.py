"""
Audit an IAL chapterwise print book (P1, P2, S1, M1) by reading it back.

Independent of the builder: it reads only the finished interior PDFs and the
print index, and checks that every question links to ITS OWN mark scheme.

For every question in the index:

  1. QUESTION PAGE  the page the index names carries the question's printed
                    number, and the board's fence "(Total for Question <source
                    no.> is <marks> marks)" lies between that page and the next
                    question's page.
  2. THE LINK       the question pages print "mark scheme p. <N>" and N is the
                    index's mark scheme page -- or, for a question with no
                    verified scheme, "Mark scheme: <source> (grademax.me)".
  3. THE ANSWER     page N carries this question's label, and the left column
                    from that label to the next one names this source
                    question ("7(a)", "7.") and no other. IAL schemes print no
                    question number in their totals, so the board's own
                    question cells are the evidence that the answer is right.
  4. CONTENTS       every chapter entry in the contents points at a page that
                    opens that chapter.

Run on the interior books (before finalize), because finishing redraws the
"(Total for Question N...)" bands to the workbook's numbering.

    python scripts/audit_ial_workbook_print.py --unit m1
    python scripts/audit_ial_workbook_print.py --unit p1 --part all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz

WORKBOOK = Path(__file__).resolve().parent.parent / "data" / "workbook"
UNITS = {"p1": "P1", "p2": "P2", "s1": "S1", "m1": "M1"}

QP_FENCE = re.compile(r"Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=|:)?\s*(\d{1,3})\s+marks?", re.I)
# Papers before 2022 print a fence without the question number: "(Total 6 marks)".
OLD_FENCE = re.compile(r"\(\s*Total\s+(\d{1,3})\s+marks?\s*\)", re.I)
# A label strip in the mark scheme book: "3.1 Q4  ·  January 2019 Q7".
TAG_RE = re.compile(r"^\d\.\d+ Q\d+\s+·\s+[A-Za-z/]+ \d{4} Q\d+")
# A question cell in the scheme's left column that names a part.
CELL_RE = re.compile(r"^(\d{1,2})\s*(?:\.(?!\d)|\(\s*[a-h]\s*\)|[a-h](?![a-z])|\(\s*i+\s*\))")
# A one-part question's cell is the bare number.
BARE_RE = re.compile(r"^(\d{1,2})$")
# No IAL unit paper runs past 15 questions; larger numbers are data in the working.
MAX_QUESTION = 15
# The scheme's question column sits in the left part of the sheet.
CELL_MAX_X = 0.25


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def lines_of(page: fitz.Page) -> list[tuple[float, float, str]]:
    """(y, x, text) per line, in the line's own reading frame.

    A landscape scheme is turned onto a portrait sheet, so its text runs down
    the page; its question column is then measured along y, not x. Such lines
    get y = page height (after any horizontal label on the sheet) so a turned
    sheet's whole scheme belongs to the label above it.
    """
    found = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not text:
                continue
            dx, dy = line["dir"]
            x0, y0, x1, y1 = line["bbox"]
            if abs(dy) > abs(dx):
                across = y0 if dy > 0 else page.rect.height - y1
                found.append((page.rect.height - 1.0, across * page.rect.width / page.rect.height, text))
            else:
                found.append((y0, x0, text))
    return sorted(found)


def tags_in(book: fitz.Document) -> list[tuple[int, float, str]]:
    return [(index, y, text) for index, page in enumerate(book)
            for y, _, text in lines_of(page) if TAG_RE.match(text)]


def cells_between(book: fitz.Document, start: tuple[int, float],
                  end: tuple[int, float] | None) -> tuple[list[int], list[int]]:
    """(part-named cells, bare-number cells) in the scheme's question column."""
    numbers, bare = [], []
    last = book.page_count - 1 if end is None else end[0]
    for index in range(start[0], last + 1):
        limit = book[index].rect.width * CELL_MAX_X
        for y, x, text in lines_of(book[index]):
            if index == start[0] and y <= start[1]:
                continue
            if end is not None and index == end[0] and y >= end[1]:
                continue
            if x >= limit:
                continue
            for pattern, found in ((CELL_RE, numbers), (BARE_RE, bare)):
                match = pattern.match(text)
                if match and 1 <= int(match.group(1)) <= MAX_QUESTION:
                    found.append(int(match.group(1)))
    return numbers, bare


def audit_volume(unit: str, part: str) -> int:
    token = UNITS[unit]
    folder = WORKBOOK / unit / "print"
    index_path = folder / f"print_index_paged{part.lower()}.json"
    qp_path = folder / f"GradeMax_{token}_Workbook_Paged{part}.pdf"
    ms_path = folder / f"GradeMax_{token}_Workbook_MarkSchemes_Paged{part}.pdf"
    for path in (index_path, qp_path, ms_path):
        if not path.is_file():
            print(f"  missing: {path}")
            return 1

    entries = json.loads(index_path.read_text(encoding="utf-8"))["questions"]
    qp, ms = fitz.open(qp_path), fitz.open(ms_path)
    problems: list[str] = []
    unlinked = 0

    # -- 1 + 2: question pages and their links ------------------------------
    starts = sorted(e["workbook_page"] for e in entries)
    for entry in entries:
        page_no = entry["workbook_page"]
        source_q = int(entry["source"].rsplit("Q", 1)[1])
        later = [p for p in starts if p > page_no]
        stop = (later[0] if later else qp.page_count) - 1
        span = flat(" ".join(qp[i].get_text() for i in range(page_no - 1, max(page_no, stop))))
        first = flat(qp[page_no - 1].get_text())

        fences = {(int(a), int(b)) for a, b in QP_FENCE.findall(span)}
        old = {int(m) for m in OLD_FENCE.findall(span)}
        if (source_q, entry["marks"]) not in fences and entry["marks"] not in old:
            problems.append(f"{entry['slug']}: fence Q{source_q}={entry['marks']} "
                            f"not found from p.{page_no} (found {sorted(fences)})")
        if not re.search(rf"(?<!\d){entry['printed_number']}(?!\d)", first):
            problems.append(f"{entry['slug']}: printed number {entry['printed_number']} "
                            f"not on p.{page_no}")
        link = entry["markscheme_page"]
        if link is None:
            unlinked += 1
            if f"mark scheme: {entry['source']} (grademax.me)" not in span.lower().replace(entry['source'].lower(), entry['source']):
                problems.append(f"{entry['slug']}: no scheme page and no fallback reference")
        elif not re.search(rf"mark scheme p\. {link}(?!\d)", span, re.I):
            problems.append(f"{entry['slug']}: question pages do not print 'Mark scheme p. {link}'")

    # -- 3: the answer the link points at -----------------------------------
    tags = tags_in(ms)
    for entry in entries:
        link = entry["markscheme_page"]
        if link is None:
            continue
        wanted = f"{entry['section']} Q{entry['printed_number']} "
        mine = [t for t in tags if t[0] == link - 1 and t[2].startswith(wanted)]
        if not mine:
            problems.append(f"{entry['slug']}: label '{wanted.strip()}' not on mark scheme p.{link}")
            continue
        at = tags.index(mine[0])
        following = tags[at + 1] if at + 1 < len(tags) else None
        cells, bare = cells_between(ms, mine[0][:2], following[:2] if following else None)
        source_q = int(entry["source"].rsplit("Q", 1)[1])
        # A one-part question prints only the bare number; working values are
        # bare numbers too, so a bare number can confirm but never accuse.
        if source_q not in cells and source_q not in bare:
            problems.append(f"{entry['slug']}: answer block never names question {source_q} "
                            f"(cells {sorted(set(cells))})")
        others = sorted({n for n in cells if n != source_q})
        if others:
            problems.append(f"{entry['slug']}: answer block for Q{source_q} also names {others}")

    # -- 4: contents -> chapter openers ------------------------------------
    chapters = sorted({(e["chapter"], e["chapter_title"]) for e in entries})
    contents_text = flat(" ".join(qp[i].get_text() for i in range(min(16, qp.page_count))))
    for number, title in chapters:
        match = re.search(rf"{number} {re.escape(title)} (\d+)", contents_text)
        if not match:
            problems.append(f"contents: chapter {number} not listed")
            continue
        opener = flat(qp[int(match.group(1)) - 1].get_text())
        if f"Chapter {number}" not in opener or title not in opener:
            problems.append(f"contents: chapter {number} points at p.{match.group(1)}, "
                            f"which does not open it")

    print(f"\n  {token}{part or ' (one volume)'}: {len(entries)} questions "
          f"({unlinked} without a verified scheme), {qp.page_count} + {ms.page_count} pages, "
          f"{len(tags)} answer labels")
    for problem in problems[:40]:
        print(f"    {problem}")
    if len(problems) > 40:
        print(f"    ... and {len(problems) - 40} more")
    print(f"    -> {len(problems)} problem(s)")
    return len(problems)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit", required=True, choices=sorted(UNITS))
    parser.add_argument("--part", choices=("1", "2", "all"))
    args = parser.parse_args()
    parts = {"all": ["_Part1", "_Part2"], "1": ["_Part1"], "2": ["_Part2"], None: [""]}[args.part]
    total = sum(audit_volume(args.unit, part) for part in parts)
    print(f"\n  TOTAL PROBLEMS: {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
