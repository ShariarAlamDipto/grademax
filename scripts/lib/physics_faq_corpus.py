"""Read the segmented Edexcel IGCSE Physics archive into a de-duplicated question corpus.

The archive contains a number of mislabelled duplicate paper folders (for example
2019_Jan_P1 holds a byte-identical copy of 2018_Jan_P1). Counting those would inflate
every 'how often is this asked' figure, so identical question texts are collapsed to a
single canonical copy - the earliest sitting that carries them.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz

FOLDER_RE = re.compile(r"^(\d{4})_([A-Za-z-]+)_P(\d)(R?)$")
TOTAL_RE = re.compile(r"Total for Question\s*(\d+)\s*=\s*(\d+)\s*mark", re.I)
SESSION_ORDER = {"Jan": 0, "May-Jun": 1, "Oct-Nov": 2}

_DROP_LINE = (
    re.compile(r"DO NOT WRITE IN THIS AREA", re.I),
    re.compile(r"GradeMax"),
    re.compile(r"^\*?P\d{4,6}A?\d*\*?$"),
    re.compile(r"^4PH[01]\s*\|"),
    re.compile(r"^(Physics|Chemistry)\s*[^\w]\s*\d{4}"),
)


def _clean(text: str) -> str:
    out = []
    for raw in text.replace("\xa0", " ").split("\n"):
        line = raw.strip()
        if not line or any(p.search(line) for p in _DROP_LINE):
            continue
        out.append(line)
    return "\n".join(out)


def _read_pdf(path: Path) -> str:
    try:
        with fitz.open(path) as doc:
            return _clean("\n".join(page.get_text() for page in doc))
    except Exception:
        return ""


def _sort_key(row: dict) -> tuple:
    return (row["year"], SESSION_ORDER.get(row["session"], 9),
            row["paper"], row["variant"], row["q"])


def _text_hash(text: str) -> str:
    words = re.findall(r"[a-z]+|\d+", text.lower())
    return hashlib.md5(" ".join(words).encode()).hexdigest()


def _marks_from_footer(qp_text: str, q_number: int) -> int | None:
    """Ground-truth mark tariff, read off the paper's own 'Total for Question N' footer."""
    for num, marks in TOTAL_RE.findall(qp_text):
        if int(num) == q_number:
            return int(marks)
    return None


def _load_topics(topics_path: Path) -> dict[str, str]:
    """Map 'paper_folder/qN' -> chapter number, from the classified question index."""
    import json
    mapping: dict[str, str] = {}
    if not topics_path.exists():
        return mapping
    for line in topics_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        src = (row.get("source_qp") or "").replace("\\", "/")
        if not src or not row.get("primary_topic"):
            continue
        parts = src.split("/")
        if len(parts) >= 3:
            mapping[f"{parts[-3]}/{Path(parts[-1]).stem}"] = str(row["primary_topic"])
    return mapping


def _scan(archive: Path, from_year: int, to_year: int) -> list[dict]:
    rows = []
    for folder in sorted(p for p in archive.iterdir() if p.is_dir()):
        m = FOLDER_RE.match(folder.name)
        if not m:
            continue
        year = int(m.group(1))
        if not from_year <= year <= to_year:
            continue
        pages = folder / "pages"
        if not pages.is_dir():
            continue
        for pdf in sorted(pages.glob("*.pdf"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)):
            q_number = int(re.sub(r"\D", "", pdf.stem) or 0)
            qp_text = _read_pdf(pdf)
            if not qp_text:
                continue
            rows.append({
                "paper_id": folder.name,
                "year": year,
                "session": m.group(2),
                "paper": m.group(3),
                "variant": m.group(4),
                "q": q_number,
                "qp_text": qp_text,
                "marks_real": _marks_from_footer(qp_text, q_number),
            })
    return rows


def build_corpus(archive: Path, from_year: int = 2018, to_year: int = 2025,
                 topics_path: Path | None = None) -> tuple[list[dict], list[str]]:
    """Return (canonical questions, human-readable report lines)."""
    rows = _scan(archive, from_year, to_year)

    if topics_path is None:
        topics_path = archive.parent.parent / "analysis" / "4PH1" / "questions.jsonl"
    topics = _load_topics(topics_path)
    for row in rows:
        row["topic"] = topics.get(f"{row['paper_id']}/q{row['q']}")

    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(_text_hash(row["qp_text"]), []).append(row)

    canonical = sorted((sorted(g, key=_sort_key)[0] for g in groups.values()), key=_sort_key)

    dropped = len(rows) - len(canonical)
    dup_papers = sorted({r["paper_id"] for g in groups.values() if len(g) > 1
                         for r in g[1:]})
    report = [
        f"{len(rows)} question PDFs read from {len({r['paper_id'] for r in rows})} paper folders",
        f"{dropped} duplicate copies collapsed "
        f"({len(dup_papers)} folders were re-used or mislabelled)",
        f"canonical corpus: {len(canonical)} questions from "
        f"{len({r['paper_id'] for r in canonical})} distinct papers",
        f"{sum(1 for r in canonical if r.get('topic'))} of {len(canonical)} "
        f"questions carry a chapter classification",
    ]
    return canonical, report
