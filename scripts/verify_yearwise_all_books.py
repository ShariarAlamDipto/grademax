"""
Independent check of the FINISHED 2018-2026 yearwise books: reads only the
interior PDFs (no print_index, no build code), and proves every printed
cross-reference lands where it says.

For each volume pair:
  * page count <= 450 (binding limit) and every sheet numbered 1..n in order;
  * every "Mark scheme: Qn p. N" on a question sheet -> page N of the scheme
    book is headed with the SAME paper and sitting, and question n's answers
    are on N (or start at its foot and run onto N+1);
  * every "Question paper: p. M" on a scheme sheet -> page M of the question
    book is headed with the same paper and sitting;
  * no paper's cover sheet and no "BLANK PAGE" sheet was printed.

    python -X utf8 scripts/verify_yearwise_all_books.py data/yearwise_all/books/igcse_mathsb
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

# _nbsp_patched: embedded Arial extracts its spaces as U+00A0.
_get_text = fitz.Page.get_text
fitz.Page.get_text = lambda self, *a, **k: (lambda r: r.replace(" ", " ") if isinstance(r, str) else r)(_get_text(self, *a, **k))

LIMIT = 450
HEAD = re.compile(r"^(.*?)\s+[|·]\s+(\w+(?:/\w+)? \d{4})", re.M)
MS_REF = re.compile(r"Q(\d+) p\. (\d+)")
QP_REF = re.compile(r"Question paper: p\. (\d+)")
COVER = re.compile(r"Please check the examination details below|Candidate surname", re.I)
BLANK = re.compile(r"BLANK\s+PAGE", re.I)


def head(page: fitz.Page) -> tuple[str, str] | None:
    """(paper, sitting) from the running head, e.g. ('Paper 1', 'May/June 2024')."""
    top = page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, 30))
    m = HEAD.search(top)
    return (m.group(1).strip(), m.group(2)) if m else None


def answers_on(page: fitz.Page, q: int) -> bool:
    text = page.get_text()
    return bool(re.search(rf"(?m)^\s*{q}\s*(?:\(|$|\.|[a-z]\b)|Total\s+for\s+[Qq]uestion\s+{q}\b", text)
                or re.search(rf"(?m)^\s*{q}\s*$", text))


def check_pair(qpath: Path, mpath: Path) -> list[str]:
    errs: list[str] = []
    q, m = fitz.open(qpath), fitz.open(mpath)
    for doc, name in ((q, qpath.name), (m, mpath.name)):
        if doc.page_count > LIMIT:
            errs.append(f"{name}: {doc.page_count} pages > {LIMIT}")
        for i, page in enumerate(doc, 1):
            foot = page.get_text("text", clip=fitz.Rect(0, page.rect.height - 30, page.rect.width,
                                                          page.rect.height))
            if not re.search(rf"(?<!\d){i}(?!\d)", foot):
                errs.append(f"{name} p{i}: page number not printed")
    links = checked = 0
    for i, page in enumerate(q, 1):
        h = head(page)
        top = page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, 30))
        if i > 2 and COVER.search(page.get_text()) and "Formulae" not in top:
            errs.append(f"question p{i}: an exam cover sheet was printed")
        body = page.get_text("text", clip=fitz.Rect(0, 40, page.rect.width, page.rect.height - 50))
        if BLANK.search(body) and len(body.strip()) < 200:
            errs.append(f"question p{i}: a BLANK PAGE sheet was printed")
        if "Mark scheme:" not in top or h is None:
            continue
        for qn, target in MS_REF.findall(top):
            links += 1
            t = int(target)
            if not 1 <= t <= m.page_count:
                errs.append(f"question p{i} Q{qn}: scheme page {t} does not exist")
                continue
            mh = head(m[t - 1])
            if not mh or mh[0] != h[0] or mh[1] != h[1]:
                errs.append(f"question p{i} {h} Q{qn} -> scheme p{t} is headed {mh}")
                continue
            near = [m[t - 1]] + ([m[t]] if t < m.page_count else [])
            if any(answers_on(pg, int(qn)) for pg in near):
                checked += 1
            else:
                errs.append(f"question p{i} {h} Q{qn} -> scheme p{t}: question {qn} not found there")
    back = 0
    for i, page in enumerate(m, 1):
        top = page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, 30))
        r = QP_REF.search(top)
        h = head(page)
        if not r or not h:
            continue
        t = int(r.group(1))
        qh = head(q[t - 1]) if 1 <= t <= q.page_count else None
        if not qh or qh != h:
            errs.append(f"scheme p{i} {h} -> question p{t} is headed {qh}")
        else:
            back += 1
    print(f"  {qpath.name}: {q.page_count}pp, {mpath.name}: {m.page_count}pp | "
          f"{links} question->scheme links, {checked} land on their question | "
          f"{back} scheme->question links verified")
    return errs


def main() -> int:
    folder = Path(sys.argv[1])
    errs: list[str] = []
    for qpath in sorted(folder.glob("*_Questions_interior.pdf")):
        mpath = qpath.with_name(qpath.name.replace("_Questions_", "_MarkSchemes_"))
        errs += check_pair(qpath, mpath)
    for e in errs[:60]:
        print("  !", e)
    print(f"{folder.name}: {'PASS' if not errs else f'{len(errs)} problems'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
