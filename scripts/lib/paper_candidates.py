"""Candidate documents for replacing a wrongly-paired QP or MS.

Sources, in the order they are trusted:
  1. Pearson's own catalogue (Algolia index) -- authoritative, fetched on demand.
  2. The local archives `data/Ultimate Final IGCSE` and `data/Ultimate Final IAL`.
  3. Other live rows' files (a swapped pair names each other's documents).

Every candidate is parsed with `paper_fingerprint.read_pdf`, so it carries the
same identity + content tokens as the live documents it will be scored against.
"""

from __future__ import annotations

import hashlib
import pickle
import re
from pathlib import Path
from urllib.parse import quote

import httpx

import fitz

from lib.paper_fingerprint import content_tokens, identify, read_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = (REPO_ROOT / "data" / "Ultimate Final IGCSE",
            REPO_ROOT / "data" / "Ultimate Final IAL")
CACHE = REPO_ROOT / "data" / "analysis" / ".pairing_cache" / "candidates"
PARSE_VERSION = "v5"

# DB subject name -> archive folder(s). IAL maths units share two folders.
IGCSE_FOLDER = {
    "Accounting": "Accounting", "Bangla": "Bangla", "Biology": "Biology",
    "Business Studies": "Business_Studies", "Chemistry": "Chemistry",
    "Commerce": "Commerce", "Computer Science": "Computer_Science",
    "Economics": "Economics", "English Language A": "English_A",
    "English Language B": "English_B", "Further Pure Mathematics": "Further_Pure_Maths",
    "Geography": "Geography", "Human Biology": "Human_Biology", "ICT": "ICT",
    "Mathematics A": "Mathematics_A", "Mathematics B": "Mathematics_B",
    "Mechanics 1": "Mechanics_1", "Physics": "Physics",
}


def archive_folders(level: str, subject: str) -> list[Path]:
    if level == "IGCSE":
        folder = IGCSE_FOLDER.get(subject)
        return [ARCHIVES[0] / folder] if folder else []
    if not subject.startswith("IAL "):
        # single-unit maths subjects; M1 also lives in the IGCSE tree
        return [ARCHIVES[1] / "Mathematics", ARCHIVES[1] / "Further_Mathematics",
                ARCHIVES[0] / "Mechanics_1"]
    return [ARCHIVES[1] / subject[4:].replace(" ", "_")]


MIN_TEXT_CHARS = 1500
_OCR = None


def ocr_pages(body: bytes) -> list[str]:
    """OCR every page. Some third-party copies (AutomatePapers' 2019 M3 QP)
    are scans with no text layer at all, so neither identity nor content can
    be read any other way."""
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    doc = fitz.open(stream=body, filetype="pdf")
    try:
        out = []
        for page in doc:
            result, _ = _OCR(page.get_pixmap(dpi=150).tobytes("png"))
            out.append(" ".join(item[1] for item in (result or [])))
        return out
    finally:
        doc.close()


def parse_file(path: Path, ocr_if_empty: bool = False) -> dict | None:
    """read_pdf of a local file, memoised on (path, size, mtime). With
    `ocr_if_empty`, a file without a usable text layer is OCR'd instead."""
    st = path.stat()
    key = hashlib.sha1(f"{path}|{st.st_size}|{st.st_mtime_ns}|{PARSE_VERSION}|"
                       f"{ocr_if_empty}".encode()).hexdigest()
    pkl = CACHE / f"{key}.pkl"
    if pkl.is_file():
        return pickle.loads(pkl.read_bytes())
    try:
        body = path.read_bytes()
        info = read_pdf(body)
        if ocr_if_empty and info["chars"] < MIN_TEXT_CHARS:
            pages = ocr_pages(body)
            info = {"ident": identify(pages[:3] + pages[-1:]),
                    "tokens": content_tokens(pages), "pages": len(pages),
                    "chars": sum(len(p) for p in pages), "ocr": True}
    except Exception:  # noqa: BLE001 -- unreadable candidate is simply not a candidate
        return None
    info["source"] = str(path.relative_to(REPO_ROOT))
    info["path"] = str(path)
    CACHE.mkdir(parents=True, exist_ok=True)
    pkl.write_bytes(pickle.dumps(info))
    return info


def local_candidates(level: str, subject: str, kind: str) -> list[Path]:
    out = []
    for folder in archive_folders(level, subject):
        if folder.is_dir():
            out += [p for p in folder.rglob("*.pdf") if p.stem.upper().endswith("_" + kind)]
    return out


# ── Pearson catalogue ────────────────────────────────────────────────────────

APP_ID = "L639T95U5A"
API_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"   # public search-only key, embedded in Pearson's site
INDEX = "qualifications-uk_LIVE_master-content"
ALGOLIA = (f"https://{APP_ID.lower()}-dsn.algolia.net/1/indexes/{INDEX}/query"
           f"?x-algolia-application-id={APP_ID}&x-algolia-api-key={API_KEY}")
PEARSON_HOST = "https://qualifications.pearson.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "Chrome/126 Safari/537.36"}
FAMILY = {"IGCSE": "International-GCSE", "IAL": "International-Advanced-Level"}

# DB subject -> Pearson Qualification-Subject slugs
PEARSON_SLUG = {
    "Mathematics A": ["Mathematics-A"], "Mathematics B": ["Mathematics-B"],
    "Further Pure Mathematics": ["Further-Pure-Mathematics"],
    "English Language A": ["English-Language-A"], "English Language B": ["English-Language-B"],
    "Business Studies": ["Business"], "Human Biology": ["Human-Biology"],
    "Computer Science": ["Computer-Science"], "Mechanics 1": ["Mathematics"],
    "ICT": ["Information-and-Communication-Technology", "ICT"],
    "Bangla": ["Bangla", "Bengali"],
}


def pearson_slugs(level: str, subject: str) -> list[str]:
    if subject in PEARSON_SLUG:
        return PEARSON_SLUG[subject]
    if level == "IAL" and not subject.startswith("IAL "):
        return ["Mathematics"]
    return [subject.removeprefix("IAL ").replace(" ", "-")]


_HITS: dict[tuple, list] = {}


def pearson_hits(level: str, subject: str) -> list[dict]:
    """Every PDF asset Pearson lists for the subject: [{url, title}]."""
    key = (level, subject)
    if key in _HITS:
        return _HITS[key]
    hits = []
    for slug in pearson_slugs(level, subject):
        filters = (f'category:"Pearson-UK:Qualification-Family/{FAMILY[level]}"'
                   f' AND category:"Pearson-UK:Qualification-Subject/{slug}"'
                   ' AND type:"dam:Asset"')
        page = 0
        while page < 20:
            payload = {"params": f"query=&filters={quote(filters, safe='')}"
                                 f"&hitsPerPage=1000&page={page}"}
            try:
                r = httpx.post(ALGOLIA, json=payload, timeout=30)
            except httpx.HTTPError:
                break
            if r.status_code != 200:
                break
            data = r.json()
            for h in data.get("hits", []):
                url = h.get("url") or h.get("path") or ""
                if url.lower().endswith(".pdf"):
                    hits.append({"url": url if url.startswith("http") else PEARSON_HOST + url,
                                 "title": h.get("title") or "",
                                 "category": [str(c) for c in (h.get("category") or [])]})
            if page + 1 >= data.get("nbPages", 1):
                break
            page += 1
        if hits:
            break
    _HITS[key] = hits
    return hits


def pearson_kind(hit: dict) -> str | None:
    u = hit["url"].lower()
    cats = " ".join(hit["category"]).lower()
    if "document-type/mark" in cats or "mark scheme" in hit["title"].lower() \
            or re.search(r"[-_](rms|msc|ms)[-_.]", u):
        return "MS"
    if "document-type/question" in cats or "question paper" in hit["title"].lower() \
            or re.search(r"[-_]que[-_.]", u):
        return "QP"
    return None


def pearson_series(hit: dict) -> tuple[int | None, str | None]:
    season_of = {"january": "jan", "february": "jan", "march": "jan", "may": "may-jun",
                 "june": "may-jun", "summer": "may-jun", "october": "oct-nov",
                 "november": "oct-nov", "winter": "oct-nov"}
    for c in hit["category"]:
        m = re.search(r"Exam-Series/([A-Za-z]+)-(\d{4})", c)
        if m and m.group(1).lower() in season_of:
            return int(m.group(2)), season_of[m.group(1).lower()]
    return None, None


def fetch_pearson(url: str) -> dict | None:
    """Download + parse a Pearson asset. Their `/secure/` paths return an HTML
    login page with status 200, so the %PDF magic is the only real test."""
    pkl = CACHE / (hashlib.sha1(f"{url}|{PARSE_VERSION}".encode()).hexdigest() + ".pkl")
    raw = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
    if pkl.is_file():
        return pickle.loads(pkl.read_bytes())
    CACHE.mkdir(parents=True, exist_ok=True)
    if not raw.is_file():
        try:
            r = httpx.get(url, headers=UA, timeout=60, follow_redirects=True)
        except httpx.HTTPError:
            return None
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return None
        raw.write_bytes(r.content)
    try:
        info = read_pdf(raw.read_bytes())
    except Exception:  # noqa: BLE001
        return None
    info["source"] = url
    info["path"] = str(raw)
    pkl.write_bytes(pickle.dumps(info))
    return info
