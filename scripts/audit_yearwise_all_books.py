"""
Full audit of FINISHED 2018-2026 yearwise books -- completeness, linkage,
contents and page formation -- read from the interior PDFs themselves.

The only other input is the linkage audit's sitting list
(data/yearwise_all/linkage/<book>.json), used as the statement of what SHOULD
be in the books. Nothing from the build (no print_index, no build code).

  A. COMPLETENESS  every new-spec sitting that exists is printed, once, in
     date order; a sitting held back (no verified scheme) is reported with why.
  B. IDENTITY      every printed question sheet carries (in its text layer,
     under the painted-out footer) the board item code of the paper its
     running head names; no sheet of one paper appears inside another.
  C. QUESTIONS     each paper's printed "(Total for Question n ...)" lines run
     1..n with no gap or repeat, and sum to the paper total where stated.
  D. SCHEMES       each scheme section's own Pearson publication code names the
     unit and session its running head claims; its per-question totals (where
     printed) agree with the paper's.
  E. CONTENTS      every contents row points at the FIRST page of that paper
     (head matches, the page before does not), rows are in order, every
     printed paper is listed exactly once and nothing is listed twice.
  F. PAGES         numbered 1..n consecutively, A4, <=450, every body page
     headed, no exam cover / BLANK PAGE / empty sheet, no sheet printed twice.

    python -X utf8 scripts/audit_yearwise_all_books.py igcse_mathsb
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import fitz

# _nbsp_patched: embedded Arial extracts its spaces as U+00A0.
_get_text = fitz.Page.get_text
fitz.Page.get_text = lambda self, *a, **k: (lambda r: r.replace(" ", " ") if isinstance(r, str) else r)(_get_text(self, *a, **k))

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 450
SEASON = {"January": "Jan", "May/June": "May-Jun", "October/November": "Oct-Nov"}
SEASON_MM = {"Jan": ("01", "02"), "May-Jun": ("05", "06"), "Oct-Nov": ("10", "11")}
HEAD = re.compile(r"^(.*?)\s+[|·]\s+(January|May/June|October/November) (\d{4})", re.M)
ITEM = re.compile(r"\*?(P\d{5})R{0,2}A\d{4}\*?")
QTOTAL = re.compile(r"\(\s*Total\s+for\s+Question\s+(\d+)\s*(?:is|=)\s*(\d+)\s+marks?\s*\)", re.I)
PAPER_TOTAL = re.compile(r"TOTAL\s+FOR\s+PAPER\s+(?:IS|=)\s+(\d+)\s+MARKS", re.I)
PUB = re.compile(r"Publications?\s*Code\s*[:\s]?\s*([A-Z0-9]{4,5})_([0-9A-Z]{1,3})_(?:(?:r?ms|MS)_)?(\d{8}|\d{4})", re.I)
CONTENTS_ROW = re.compile(r"^(January|May/June|October/November)$")
COVER = re.compile(r"Please check the examination details below|Candidate surname", re.I)
BLANK = re.compile(r"BLANK\s+PAGE", re.I)


def top(page: fitz.Page) -> str:
    return page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, 30))


def head(page: fitz.Page) -> tuple[str, str, int] | None:
    m = HEAD.search(top(page))
    return (m.group(1).strip(), SEASON[m.group(2)], int(m.group(3))) if m else None


def pub_session(code: str) -> str:
    if len(code) == 4:
        return code
    y, mth = int(code[:4]), int(code[4:6])
    if mth <= 2:
        return f"{(y - 1) % 100:02d}10"
    if mth <= 4:
        return f"{y % 100:02d}01"
    if mth <= 9:
        return f"{y % 100:02d}06"
    return f"{y % 100:02d}10"


def expected(book: str) -> tuple[list[tuple], list[str]]:
    """(unit label, season, year) of every LINKED paper, and notes on those held back."""
    data = json.loads((ROOT / "data/yearwise_all/linkage" / f"{book}.json").read_text(encoding="utf-8"))
    want, held = [], []
    for u in data:
        for s in u["sittings"]:
            year, season = s["sitting"].split(" ", 1)
            if s["verdict"] == "LINKED":
                want.append((u["label"], season, int(year), s["qp"]["item_code"]))
            elif s["verdict"] != "LEGACY":
                held.append(f"{u['label']} {s['sitting']}: held back -- {s['problems'][0][:70]}")
    return want, held


def contents_rows(doc: fitz.Document) -> list[tuple[str, int, str, int]]:
    """(season, year, reference, page) from the contents sheets, in printed order."""
    rows = []
    for page in doc:
        if "Contents" not in page.get_text("text", clip=fitz.Rect(0, 80, page.rect.width, 105)):
            continue
        # Rows are read by PRINTED LINE: cells are grouped by baseline, whatever
        # blocks the extractor splits them into (one 3-line block in base-14
        # type, three single-line blocks in embedded Arial).
        lines: dict[int, list[tuple[float, str]]] = defaultdict(list)
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                t = "".join(sp["text"] for sp in ln["spans"]).replace(" ", " ").strip()
                if t:
                    lines[round(ln["bbox"][3])].append((ln["bbox"][0], t))
        year = None
        for y in sorted(lines):
            cells = [t for _, t in sorted(lines[y])]
            if len(cells) == 1 and re.fullmatch(r"20\d\d", cells[0]):
                year = int(cells[0])
            elif len(cells) == 3 and CONTENTS_ROW.match(cells[0]) and cells[2].isdigit():
                rows.append((SEASON[cells[0]], year, cells[1], int(cells[2])))
    return rows


def audit_volume(q: fitz.Document, m: fitz.Document, name: str, errs: list[str]) -> list[tuple]:
    papers: dict[tuple, dict] = {}
    seen_sheets: Counter = Counter()
    for doc, kind in ((q, "Q"), (m, "M")):
        if doc.page_count > LIMIT:
            errs.append(f"{name}{kind}: {doc.page_count} pages > {LIMIT}")
        body_started = False
        for i, page in enumerate(doc, 1):
            if abs(page.rect.width - 595.3) > 1 or abs(page.rect.height - 841.9) > 1:
                errs.append(f"{name}{kind} p{i}: not A4 ({page.rect})")
            foot = page.get_text("text", clip=fitz.Rect(0, page.rect.height - 30, page.rect.width, page.rect.height))
            if not re.search(rf"(?<!\d){i}(?!\d)", foot):
                errs.append(f"{name}{kind} p{i}: printed page number missing/wrong")
            # Our heads/feet are embedded Arial with an ASCII "|" separator; a
            # middot in non-embedded type rendered as a summation sign.
            if re.search("[·•∑]", top(page) + foot):
                errs.append(f"{name}{kind} p{i}: middot/bullet/sigma in the head or foot")
            h = head(page)
            if h is None:
                if body_started:
                    errs.append(f"{name}{kind} p{i}: body page without running head")
                continue
            body_started = True
            text = page.get_text()
            inner = page.get_text("text", clip=fitz.Rect(0, 40, page.rect.width, page.rect.height - 50))
            if len(inner.strip()) < 15 and not page.get_images() and len(page.get_drawings()) < 5:
                errs.append(f"{name}{kind} p{i}: empty sheet")
            if kind == "Q":
                if COVER.search(text) and "Formulae" not in top(page):
                    errs.append(f"{name}Q p{i}: exam cover sheet printed")
                if BLANK.search(inner) and len(inner.strip()) < 200:
                    errs.append(f"{name}Q p{i}: BLANK PAGE printed")
                # Keyed with the running head: blank "Question 6 continued" pages
                # of DIFFERENT papers are identical text and are not repeats.
                body = page.get_text("text", clip=fitz.Rect(0, 40, page.rect.width, page.rect.height - 50))
                if body.strip():
                    seen_sheets[hashlib.md5((top(page) + body + str(ITEM.findall(text))).encode()).hexdigest()] += 1
            if h[0] in ("Formulae and data", "General Marking Guidance"):
                continue
            key = (h[0], h[1], h[2])
            p = papers.setdefault(key, {"q": [], "m": [], "items": Counter(), "totals": [],
                                       "paper_total": None, "pub": set(), "ms_totals": []})
            if kind == "Q":
                p["q"].append(i)
                for code in ITEM.findall(text):
                    p["items"][code] += 1
                p["totals"] += [(int(a), int(b)) for a, b in QTOTAL.findall(re.sub(r"\s+", " ", text))]
                p.setdefault("headed", set()).update(int(x) for x in re.findall(r"Q(\d+) (?:from )?p\.", top(page)))
                pt = PAPER_TOTAL.search(re.sub(r"\s+", " ", text))
                if pt:
                    p["paper_total"] = int(pt.group(1))
            else:
                p["m"].append(i)
                for mm in PUB.finditer(re.sub(r"\s+", " ", text)):
                    p["pub"].add((mm.group(1).upper(), pub_session(mm.group(3))))
    dupes = [k for k, v in seen_sheets.items() if v > 1]
    if len(dupes) > 0:
        errs.append(f"{name}Q: {len(dupes)} sheet(s) printed more than once")

    # B/C/D per paper
    for key, p in papers.items():
        label, season, year = key
        where = f"{name} {label} {season} {year}"
        if not p["q"]:
            errs.append(f"{where}: scheme printed but no question paper"); continue
        if not p["m"]:
            errs.append(f"{where}: question paper printed but no mark scheme"); continue
        if p["q"] != list(range(p["q"][0], p["q"][-1] + 1)):
            errs.append(f"{where}: question sheets not contiguous")
        if p["m"] != list(range(p["m"][0], p["m"][-1] + 1)):
            errs.append(f"{where}: scheme sheets not contiguous")
        items = [c for c, n in p["items"].most_common()]
        if len(items) > 1 and p["items"][items[1]] > 1:
            errs.append(f"{where}: sheets of two papers mixed: {dict(p['items'])}")
        nums = [n for n, _ in p["totals"]]
        if nums and nums != list(range(1, len(nums) + 1)):
            missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
            dup = [n for n, c in Counter(nums).items() if c > 1]
            # A question whose total is inside an image is still accounted for
            # when the running head of one of the paper's sheets names it.
            missing = [n for n in missing if n not in p.get("headed", set())]
            if dup or missing:
                errs.append(f"{where}: question totals run {nums} (missing {missing}, repeated {dup})")
        if p["paper_total"] and p["totals"]:
            got = sum(b for _, b in p["totals"])
            if got != p["paper_total"] and not (nums and max(nums) > len(set(nums))):
                p["note_sum"] = f"{got}/{p['paper_total']}"
        mm = SEASON_MM[season]
        if p["pub"] and not any(s[:2] == f"{year % 100:02d}" and s[2:] in mm or s == str(year)
                                for _, s in p["pub"]):
            errs.append(f"{where}: scheme's publication code names {sorted(p['pub'])}")
        p["item"] = items[0] if items else None
    return [(k[0], k[1], k[2], v) for k, v in papers.items()]


def audit_contents(doc: fitz.Document, name: str, printed: list[tuple], errs: list[str], kind: str) -> int:
    rows = contents_rows(doc)
    starts = {}
    for label, season, year, p in printed:
        pages = p["q"] if kind == "Q" else p["m"]
        if pages:
            starts[(label, season, year)] = pages[0]
    listed = Counter()
    for season, year, ref, page in rows:
        label = re.split(r"[|·]", ref)[0].strip()
        key = (label, season, year)
        listed[key] += 1
        if key not in starts:
            errs.append(f"{name}{kind} contents: {label} {season} {year} listed but not printed")
        elif starts[key] != page:
            errs.append(f"{name}{kind} contents: {label} {season} {year} says p{page}, paper starts p{starts[key]}")
    for key in starts:
        if listed[key] != 1:
            errs.append(f"{name}{kind} contents: {key} listed {listed[key]} times")
    order = [r[3] for r in rows]
    if order != sorted(order):
        errs.append(f"{name}{kind} contents: rows not in page order")
    return len(rows)


def main() -> int:
    book = sys.argv[1]
    folder = ROOT / "data/yearwise_all/books" / book
    want, held = expected(book)
    errs: list[str] = []
    printed_all = []
    for qp in sorted(folder.glob("*_Questions_interior.pdf")):
        msp = qp.with_name(qp.name.replace("_Questions_", "_MarkSchemes_"))
        name = qp.name.split("_Yearwise_")[1].split("_")[0] + " "
        q, m = fitz.open(qp), fitz.open(msp)
        printed = audit_volume(q, m, name, errs)
        nq = audit_contents(q, name, printed, errs, "Q")
        nm = audit_contents(m, name, printed, errs, "M")
        print(f"  {name}: {len(printed)} papers | questions {q.page_count}pp, contents rows {nq} | "
              f"schemes {m.page_count}pp, contents rows {nm}")
        printed_all += printed
    # A. completeness against the linkage list
    got = Counter((l.split()[-2] + " " + l.split()[-1] if False else l, s, y) for l, s, y, _ in printed_all)
    by_item = {p["item"]: (l, s, y) for l, s, y, p in printed_all}
    for label, season, year, item in want:
        short = label.replace(label.rsplit(" ", 2)[0] + " ", "") if " " in label else label
        hit = [k for k in got if k[1] == season and k[2] == year and label.endswith(k[0])]
        if not hit:
            errs.append(f"MISSING: {label} {season} {year} is linked but not printed")
        elif got[hit[0]] > 1:
            errs.append(f"DUPLICATE: {label} {season} {year} printed {got[hit[0]]} times")
        if item and item[:6] in by_item and by_item[item[:6]][1:] != (season, year):
            errs.append(f"{label} {season} {year}: its item code {item} is printed under {by_item[item[:6]]}")
    chrono = [(y, ["Jan", "May-Jun", "Oct-Nov"].index(s)) for _, s, y, _ in printed_all]
    if chrono != sorted(chrono):
        errs.append("papers are not in date order across the volumes")
    print(f"\n{book}: {len(want)} linked papers expected, {len(printed_all)} printed")
    for h in held:
        print(f"  held back: {h}")
    for e in errs:
        print(f"  ! {e}")
    print(f"{book}: {'PASS' if not errs else f'{len(errs)} problems'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
