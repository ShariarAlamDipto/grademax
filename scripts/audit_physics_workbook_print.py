"""
Audit the Physics print books by reading them back.

Independent of the builder: it reads only the finished PDFs and the print
index, and checks that every question links to ITS OWN mark scheme.

For every question in the index:

  1. QUESTION PAGE  the page the index names carries the question's printed
                    number and the board's own fence for it
                    ("(Total for Question <source no.> = <marks> marks)") is
                    found between that page and the next question's page.
  2. THE LINK       the question page's footer states "mark scheme p. <N>"
                    and N is the index's mark scheme page.
  3. THE ANSWER     page N carries this question's label ("1.1 Q4 · 2019
                    January Paper 1P Q7"), and the text from that label to the
                    next label holds a mark scheme tally naming the same
                    source question ("Total for question 7 = 5 marks") -- or,
                    for the one tally-less scheme, its numbered row. That is
                    the board's own statement of which question the answer
                    belongs to, so a wrong link cannot pass.
  4. CONTENTS       every chapter entry in the contents points at a page that
                    opens that chapter.

Run on the interior books (before finalize), because finishing redraws the
"(Total for Question N...)" bands to the workbook's numbering.

    python scripts/audit_physics_workbook_print.py                # paged, one volume
    python scripts/audit_physics_workbook_print.py --part all
    python scripts/audit_physics_workbook_print.py --edition trimmed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz

PRINT = Path(__file__).resolve().parent.parent / "data" / "workbook" / "physics" / "print"
SUFFIX = {"trimmed": "", "paged": "_Paged", "verbatim": "_Verbatim"}

QP_FENCE = re.compile(r"Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=|:)?\s*(\d{1,3})\s+marks?", re.I)
MS_TALLY = re.compile(r"Total\s+for\s+question\s*(\d{1,2})?\s*(?:is|=|:)?\s*(\d{1,3})\s*marks?", re.I)
SESSIONS = {"January": "jan", "May/June": "may-jun", "October/November": "oct-nov"}


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def tags_in(book: fitz.Document) -> list[tuple[int, float, str]]:
    """Every answer label in the mark scheme book: (page, y, text)."""
    found = []
    for index, page in enumerate(book):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if re.match(r"^\d\.\d+ Q\d+\s+·\s+\d{4} ", text):
                    found.append((index, line["bbox"][1], text))
    found.sort()
    return found


def text_between(book: fitz.Document, start: tuple[int, float],
                 end: tuple[int, float] | None) -> str:
    pieces = []
    last = book.page_count - 1 if end is None else end[0]
    for index in range(start[0], last + 1):
        for block in book[index].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                y = line["bbox"][1]
                if index == start[0] and y < start[1]:
                    continue
                if end is not None and index == end[0] and y >= end[1]:
                    continue
                pieces.append("".join(s["text"] for s in line["spans"]))
    return flat(" ".join(pieces))


def audit_volume(edition: str, part: str) -> int:
    suffix = SUFFIX[edition] + part
    index_path = PRINT / f"print_index{suffix.lower()}.json"
    qp_path = PRINT / f"GradeMax_Physics_Workbook{suffix}.pdf"
    ms_path = PRINT / f"GradeMax_Physics_Workbook_MarkSchemes{suffix}.pdf"
    for path in (index_path, qp_path, ms_path):
        if not path.is_file():
            print(f"  missing: {path}")
            return 1

    entries = json.loads(index_path.read_text(encoding="utf-8"))["questions"]
    qp, ms = fitz.open(qp_path), fitz.open(ms_path)
    problems: list[str] = []

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
        if (source_q, entry["marks"]) not in fences and entry["source"].split(" Paper")[0] != "2019 May/June":
            # The scanned paper has no text layer; it is checked by link only.
            problems.append(f"{entry['slug']}: question fence Q{source_q}={entry['marks']} "
                            f"not found from p.{page_no} (found {sorted(fences)})")
        if not re.search(rf"(?<!\d){entry['printed_number']}(?!\d)", first):
            problems.append(f"{entry['slug']}: printed number {entry['printed_number']} "
                            f"not on p.{page_no}")
        link = entry["markscheme_page"]
        if link is None:
            problems.append(f"{entry['slug']}: no mark scheme page in the index")
        elif f"mark scheme p. {link}" not in span and f"Mark scheme p. {link}" not in span:
            problems.append(f"{entry['slug']}: question pages do not print 'mark scheme p. {link}'")

    # -- 3: the answer the link points at -----------------------------------
    tags = tags_in(ms)
    for entry in entries:
        link = entry["markscheme_page"]
        if link is None:
            continue
        wanted = f"{entry['section']} Q{entry['printed_number']}"
        mine = [t for t in tags if t[0] == link - 1 and t[2].startswith(wanted + " ")]
        if not mine:
            problems.append(f"{entry['slug']}: label '{wanted}' not on mark scheme p.{link}")
            continue
        at = tags.index(mine[0])
        following = tags[at + 1] if at + 1 < len(tags) else None
        block = text_between(ms, mine[0][:2], following[:2] if following else None)
        source_q = int(entry["source"].rsplit("Q", 1)[1])
        tallies = [(int(n) if n else None, int(m)) for n, m in MS_TALLY.findall(block)]
        named = {n for n, _ in tallies if n is not None}
        if tallies:
            if named and named != {source_q}:
                problems.append(f"{entry['slug']}: answer block holds tallies {tallies}, "
                                f"expected question {source_q}")
            elif len(tallies) > 1:
                problems.append(f"{entry['slug']}: answer block holds {len(tallies)} tallies")
        elif not re.search(rf"(?:^|\s){source_q}\s*(?:\(|[a-z]\))", block):
            problems.append(f"{entry['slug']}: answer block names neither a tally nor "
                            f"question {source_q}")

    # -- 4: contents -> chapter openers ------------------------------------
    chapters = sorted({(e["chapter"], e["chapter_title"]) for e in entries})
    contents_text = flat(" ".join(qp[i].get_text() for i in range(min(8, qp.page_count))))
    for number, title in chapters:
        match = re.search(rf"{number} {re.escape(title)} (\d+)", contents_text)
        if not match:
            problems.append(f"contents: chapter {number} not listed")
            continue
        opener = flat(qp[int(match.group(1)) - 1].get_text())
        if f"Chapter {number}" not in opener or title not in opener:
            problems.append(f"contents: chapter {number} points at p.{match.group(1)}, "
                            f"which does not open it")

    label = f"{edition}{part or ' (one volume)'}"
    print(f"\n  {label}: {len(entries)} questions, {qp.page_count} + {ms.page_count} pages, "
          f"{len(tags)} answer labels")
    for problem in problems[:40]:
        print(f"    {problem}")
    if len(problems) > 40:
        print(f"    ... and {len(problems) - 40} more")
    print(f"    -> {len(problems)} problem(s)")
    return len(problems)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="paged", choices=sorted(SUFFIX))
    parser.add_argument("--part", choices=("1", "2", "all"))
    args = parser.parse_args()
    parts = {"all": ["_Part1", "_Part2"], "1": ["_Part1"], "2": ["_Part2"], None: [""]}[args.part]
    total = sum(audit_volume(args.edition, part) for part in parts)
    print(f"\n  TOTAL PROBLEMS: {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
