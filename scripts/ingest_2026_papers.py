#!/usr/bin/env python3
"""Discover and ingest the 2026 Edexcel IAL + International GCSE series.

Pearson's public Algolia catalogue is the *authoritative list* of what exists in
a series: for every paper it carries the subject, unit/paper variant, document
type and the exact CDN asset URL. That list is complete for 2026 — but as of
this writing every 2026 asset still resolves to Pearson's `/content/dam/secure/`
gate (a ~1KB HTML login page) rather than a PDF, because Pearson time-locks a
series for roughly a year after it sits. Assets are re-published at a public
path when the lock lifts, so the gate is a scheduling fact, not a dead end.

This script therefore separates *discovery* from *acquisition*:

  refresh   re-query Algolia, map every hit onto our own subjects / paper
            numbers / R2 key conventions, and write the manifest.
  status    report the manifest against the DB and against live availability:
            how many papers exist, how many we hold, how many are still gated.
  ingest    acquire everything currently obtainable, via a --source adapter,
            and publish it (verify -> clean+stamp -> R2 -> papers row).

Acquisition sources (`--source`):
  pearson   the official CDN URL from the manifest. Skips anything still gated,
            so this is safe to run on a schedule: each run picks up whatever
            Pearson has released since the last one. Also clears the Oct/Nov
            2025 backlog the moment it opens.
  dir       a staging folder of already-downloaded PDFs (`--staging`), matched
            to manifest entries by paper code + variant + session + doc type.
            Use this for any source fetched outside this script.

Every file passes the same gate before it is published: page 1 must confirm the
document type, the paper code and the exam session. A file that doesn't match
the manifest entry it was fetched for is rejected, never attached.

Dry-run by default; --commit writes. Idempotent: R2 keys are HEAD-skipped and
only NULL DB columns are filled, so re-running never duplicates or overwrites.

Usage:
    python -X utf8 scripts/ingest_2026_papers.py refresh
    python -X utf8 scripts/ingest_2026_papers.py status
    python -X utf8 scripts/ingest_2026_papers.py status --probe
    python -X utf8 scripts/ingest_2026_papers.py ingest --source pearson
    python -X utf8 scripts/ingest_2026_papers.py ingest --source pearson --commit
    python -X utf8 scripts/ingest_2026_papers.py ingest --source dir --staging data/staging/2026 --commit
"""
import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import httpx
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
_saved = sys.argv
sys.argv = [sys.argv[0]]
from ingest_cambridge_papers import clean_and_stamp  # noqa: E402
from fill_edexcel_paper_gaps import (  # noqa: E402
    derive_shapes, fetch_subject_rows, fill_shape, r2_key_from_url,
)
sys.argv = _saved

import fitz  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

APP_ID = "L639T95U5A"
API_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"
INDEX = "qualifications-uk_LIVE_master-content"
ALGOLIA = (f"https://{APP_ID.lower()}-dsn.algolia.net/1/indexes/{INDEX}/query"
           f"?x-algolia-application-id={APP_ID}&x-algolia-api-key={API_KEY}")
PEARSON_HOST = "https://qualifications.pearson.com"
FAMILIES = {"IAL": "International-Advanced-Level", "IGCSE": "International-GCSE"}

MANIFEST_DIR = ROOT / "data" / "manifest"


def manifest_path(year: int) -> Path:
    return MANIFEST_DIR / f"edexcel_{year}.json"

SEASON_FROM_SERIES = {
    "january": "jan", "february": "jan", "march": "jan",
    "may": "may-jun", "june": "may-jun", "summer": "may-jun",
    "october": "oct-nov", "november": "oct-nov", "winter": "oct-nov",
}

# Pearson's paper code differs from the code stored on our `subjects` row for a
# few subjects. Maps Pearson code (or its stem) -> our subjects.code.
CODE_ALIASES = {
    "WET": "WLT",   # IAL English Literature: Pearson WET01-04, ours WLT
    "4CP0": "4CP1",  # IGCSE Computer Science: Pearson 4CP0, ours 4CP1
    "YLA1": "WLW",  # IAL Law: Pearson YLA1/YLA2, ours WLW
    "YLA2": "WLW",
}

# Pearson codes that must never be matched by their three-letter stem, because
# the stem belongs to a different subject in our table. WIT11-14 are
# Information Technology; our `WIT` is "IAL Italian", so a stem match would
# file every IT paper as Italian. (Pearson's 2026 catalogue has no IAL Italian
# at all, which suggests our Italian rows deserve their own audit.)
NO_STEM_MATCH = {"WIT11", "WIT12", "WIT13", "WIT14"}

# Subjects whose DB rows use a single paper number regardless of the unit code
# (the unit *is* the subject, e.g. "Pure Mathematics 4 (P4)" -> paper_number 1).
SINGLE_UNIT_CODE_RE = re.compile(r"^(WMA1[1-4]|WST0[1-3]|WME0[1-3]|WFM0[1-3]|WDM11)$")


# ── Algolia discovery ────────────────────────────────────────────────────────

def algolia_hits(family: str) -> list:
    filters = (f'category:"Pearson-UK:Qualification-Family/{family}" AND type:"dam:Asset"')
    hits, page = [], 0
    while page < 40:
        payload = {"params": f"query=&filters={quote(filters, safe='')}&hitsPerPage=1000&page={page}"}
        r = httpx.post(ALGOLIA, json=payload, timeout=60)
        if r.status_code != 200:
            print(f"!! Algolia {family} page {page}: HTTP {r.status_code}")
            break
        data = r.json()
        hits.extend(data.get("hits", []))
        if page + 1 >= data.get("nbPages", 1):
            break
        page += 1
    return hits


def hit_series(hit) -> tuple[int | None, str | None]:
    for c in hit.get("category") or []:
        m = re.search(r"Exam-Series/([A-Za-z]+)-(\d{4})", str(c))
        if m:
            return int(m.group(2)), SEASON_FROM_SERIES.get(m.group(1).lower())
    return None, None


def hit_kind(hit) -> str | None:
    cats = " ".join(str(c).lower() for c in (hit.get("category") or []))
    title = (hit.get("title") or "").lower()
    url_l = (hit.get("url") or hit.get("path") or "").lower()
    if "document-type/mark" in cats or "mark scheme" in title or any(x in url_l for x in ("-rms-", "-msc-")):
        return "MS"
    if "document-type/question" in cats or "question paper" in title or "-que-" in url_l:
        return "QP"
    return None


def hit_unit(hit) -> str | None:
    for c in hit.get("category") or []:
        m = re.search(r"Unit/Unit-(\d+)", str(c))
        if m:
            return m.group(1)
    m = re.search(r"unit\s*(\d+)", (hit.get("title") or "").lower())
    return m.group(1) if m else None


def parse_asset_name(url: str) -> tuple[str | None, str | None]:
    """`.../wch12-01a-que-20260512.pdf` -> ("WCH12", "01A")."""
    fn = url.rsplit("/", 1)[-1].lower()
    m = re.match(r"([0-9a-z]{4,5})-([0-9a-z]{1,4})-(que|rms|msc)-\d{8}\.pdf$", fn)
    return (m.group(1).upper(), m.group(2).upper()) if m else (None, None)


def paper_number_for(family: str, code: str, variant: str | None, unit: str | None) -> str | None:
    """Map a Pearson code/variant onto the paper_number convention we store."""
    if family == "IAL":
        if SINGLE_UNIT_CODE_RE.match(code or ""):
            return "1"
        if unit:
            return f"Unit_{unit}"
        # Fall back to the unit digit inside the code: WCH12 -> 2, WHI03 -> 3,
        # YLA2 -> 2.
        m = (re.match(r"^W[A-Z]{2}[0-9]([0-9])$", code or "")
             or re.match(r"^Y[A-Z]{2}([0-9])$", code or ""))
        return f"Unit_{m.group(1)}" if m else None
    # IGCSE: "01" -> "1", "02R" -> "2R", "1FR" -> "1FR", "2CR" -> "2CR".
    if not variant:
        return None
    v = variant.upper()
    m = re.match(r"^0*([0-9])([A-Z]*)$", v)
    return f"{m.group(1)}{m.group(2)}" if m else v


def build_manifest(year: int) -> list[dict]:
    out = []
    for fam_key, fam in FAMILIES.items():
        hits = algolia_hits(fam)
        print(f"  {fam}: {len(hits)} assets indexed")
        for h in hits:
            yr, season = hit_series(h)
            kind = hit_kind(h)
            if yr != year or not season or not kind:
                continue
            url = h.get("url") or h.get("path") or ""
            if not url.lower().endswith(".pdf"):
                continue
            code, variant = parse_asset_name(url)
            if not code:
                continue
            out.append({
                "family": fam_key, "year": yr, "season": season, "kind": kind,
                "pearson_code": code, "variant": variant, "unit": hit_unit(h),
                "title": h.get("title"), "url": url, "gated": "/secure/" in url,
            })
    # Stable order, de-duplicated on the asset URL.
    seen, uniq = set(), []
    for e in sorted(out, key=lambda e: (e["family"], e["pearson_code"], str(e["variant"]), e["season"], e["kind"])):
        if e["url"] in seen:
            continue
        seen.add(e["url"])
        uniq.append(e)
    return mark_adapted(uniq)


def mark_adapted(manifest: list[dict]) -> list[dict]:
    """Flag Pearson's adapted papers (`wch15-01a-...` beside `wch15-01-...`).

    An `-a` asset is a different document from its plain sibling — different
    paper reference and a shorter page count — and our catalogue has always
    carried the plain paper. Where both exist we mark the `-a` one so it is
    skipped by default; where `-a` is the only asset for that paper it stays.
    """
    plain = {(e["pearson_code"], (e["variant"] or "").rstrip("A"), e["season"], e["kind"])
             for e in manifest if e["variant"] and not e["variant"].endswith("A")}
    for e in manifest:
        v = e["variant"] or ""
        e["adapted"] = bool(v.endswith("A")
                            and (e["pearson_code"], v.rstrip("A"), e["season"], e["kind"]) in plain)
    return manifest


# ── Our catalogue ────────────────────────────────────────────────────────────

def load_subjects() -> dict:
    subs = requests.get(f"{SUPABASE_URL}/rest/v1/subjects",
                        headers=H, params={"select": "id,name,code,board,level", "limit": "500"},
                        timeout=60).json()
    return {s["code"].upper(): s for s in subs
            if (s.get("board") or "").lower() == "edexcel" and s.get("code")}


def match_subject(entry: dict, by_code: dict) -> dict | None:
    code = entry["pearson_code"]
    candidates = [CODE_ALIASES.get(code), CODE_ALIASES.get(code[:3]), code, code[:4]]
    if code not in NO_STEM_MATCH:
        candidates.append(code[:3])
    for candidate in candidates:
        if candidate and candidate in by_code:
            return by_code[candidate]
    return None


def annotate(manifest: list[dict], by_code: dict, include_adapted: bool = False) -> list[dict]:
    """Attach subject + paper_number to each manifest entry (in place copies)."""
    out = []
    for e in manifest:
        if e.get("adapted") and not include_adapted:
            continue
        s = match_subject(e, by_code)
        pn = paper_number_for(e["family"], e["pearson_code"], e.get("variant"), e.get("unit")) if s else None
        out.append({**e, "subject": s["name"] if s else None,
                    "subject_id": s["id"] if s else None, "paper_number": pn})
    return out


# ── Verification ─────────────────────────────────────────────────────────────

def looks_like_pdf(body: bytes, content_type: str) -> bool:
    return body[:5] == b"%PDF-" and "html" not in content_type.lower()


def verify_page1(pdf: bytes, want_kind: str, year: int, season: str, code: str) -> tuple[bool, str]:
    """Confirm a PDF really is the paper the manifest entry describes.

    Mark schemes print the session in plain text; question-paper covers do not,
    so for a QP we verify the paper code plus the copyright year and rely on
    Algolia's (authoritative) Exam-Series tag for the season.
    """
    try:
        with fitz.open(stream=pdf, filetype="pdf") as d:
            if len(d) == 0:
                return False, "empty pdf"
            flat = " ".join(d[0].get_text().split())
    except Exception as e:
        return False, f"unreadable ({e})"
    squashed = flat.upper().replace(" ", "")
    kind = "MS" if re.search(r"mark scheme|marking scheme", flat, re.I) else "QP"
    if kind != want_kind:
        return False, f"doc type {kind} != {want_kind}"
    if code and code.upper() not in squashed:
        return False, f"code {code} absent from page 1"
    if want_kind == "MS":
        sm = re.search(r"(January|February|March|May|June|Summer|October|November|Winter)\s+(20\d{2})", flat, re.I)
        if not sm:
            return False, "no session on page 1"
        if int(sm.group(2)) != year or SEASON_FROM_SERIES.get(sm.group(1).lower()) != season:
            return False, f"session {sm.group(0)} != {season} {year}"
        return True, f"ok ({sm.group(0)})"
    cy = re.search(r"(20\d{2})\s*Pearson|©\s?(20\d{2})", flat)
    cyear = int(next((g for g in (cy.groups() if cy else []) if g), 0)) or None
    if cyear is not None and cyear != year:
        return False, f"copyright {cyear} != {year}"
    return True, f"ok (QP ©{cyear})"


# ── Acquisition adapters ─────────────────────────────────────────────────────

MONTHS_FULL = ("January|February|March|April|May|June|July|August|September"
               "|October|November|December|Summer|Winter")


def identify_pdf(pdf: bytes) -> tuple[dict | None, str]:
    """Work out which paper a PDF *is*, from its own cover page.

    Edexcel prints everything needed on page 1: the paper code and variant
    ("4CH1/1CR", "WCH12/01"), the document type, and the sitting — a full date
    on a question paper ("Tuesday 3 June 2026"), a month and year on a mark
    scheme ("Mark Scheme (Results) Summer 2026"). Reading the file itself means
    the filename and the source it came from are irrelevant.
    """
    # A handful of covers are scanned images with no extractable text. Edexcel
    # repeats the paper code in the running footer, so fall back to the next
    # couple of pages rather than losing the file.
    try:
        with fitz.open(stream=pdf, filetype="pdf") as d:
            if len(d) == 0:
                return None, "empty pdf"
            pages = [" ".join(d[i].get_text().split()) for i in range(min(3, len(d)))]
    except Exception as e:
        return None, f"unreadable ({e})"
    flat = pages[0] if pages[0] else " ".join(pages)
    wide = " ".join(pages)
    if not wide.strip():
        return None, "no extractable text (scanned images throughout)"

    # Examiner reports share the mark-scheme cover layout and would otherwise be
    # filed as papers. We don't host them, so reject them outright.
    if re.search(r"examiner'?s?\s+report|principal examiner", flat, re.I):
        return None, "examiner report (not hosted)"

    kind = "MS" if re.search(r"mark scheme|marking scheme", flat, re.I) else "QP"

    # Covers write the code three different ways: "4CH1/1C" on a question paper,
    # "In Chemistry (4CH1) Paper 1C" on most mark schemes, and bare
    # "In Economics 4EC1 02" on some. Try them in that order of specificity.
    up = flat.upper()
    code_re = r"([0-9][A-Z]{2}[0-9]{1,2}|W[A-Z]{2}[0-9]{2}|Y[A-Z]{2}[0-9])"
    var_re = r"([0-9]{1,2}[A-Z]{0,2})"
    m = (re.search(rf"\b{code_re}\s*[/_]\s*{var_re}\b", up)
         or re.search(rf"\(\s*{code_re}\s*\)\s*PAPER:?\s*{var_re}\b", up)
         or re.search(rf"\(\s*{code_re}\s*/\s*{var_re}\s*\)", up)
         or re.search(rf"\bIN\s+[A-Z()\s]{{3,40}}?{code_re}\s+{var_re}\b", up)
         or re.search(rf"\b{code_re}\s+PAPER:?\s*{var_re}\b", up))
    if not m:
        return None, "no paper code on page 1 (scanned or re-rendered?)"
    code, variant = m.group(1), m.group(2)

    sm = (re.search(rf"\b\d{{1,2}}\s+({MONTHS_FULL})\s+(20\d{{2}})\b", wide, re.I)
          or re.search(rf"\b({MONTHS_FULL})\s+(20\d{{2}})\b", wide, re.I))
    if not sm:
        return None, "no exam session on page 1"
    season = SEASON_FROM_SERIES.get(sm.group(1).lower())
    year = int(sm.group(2))
    if not season:
        return None, f"unrecognised session month '{sm.group(1)}'"

    return ({"pearson_code": code, "variant": variant, "kind": kind,
             "year": year, "season": season,
             "family": "IAL" if code[0] in "WY" else "IGCSE"}, "ok")


def fetch_url(url: str, client: httpx.Client) -> tuple[bytes | None, str]:
    try:
        r = client.get(url)
    except Exception as e:
        return None, f"fetch failed ({e})"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    if not looks_like_pdf(r.content, r.headers.get("content-type", "")):
        return None, "not a PDF (login page or HTML?)"
    return r.content, f"{len(r.content) // 1024}KB"


def fetch_pearson(entry: dict, client: httpx.Client) -> tuple[bytes | None, str]:
    url = entry["url"]
    full = (url if url.startswith("http") else PEARSON_HOST + url).replace(" ", "%20")
    try:
        r = client.get(full)
    except Exception as e:
        return None, f"fetch failed ({e})"
    if not looks_like_pdf(r.content, r.headers.get("content-type", "")):
        return None, "gated (Pearson has not released this series yet)"
    return r.content, "downloaded"


def index_staging(staging: Path) -> dict:
    """Index a staging folder by (code, variant, kind) taken from the filename."""
    idx = {}
    for p in staging.rglob("*.pdf"):
        code, variant = parse_asset_name(p.name)
        if code:
            kind = "MS" if re.search(r"-(rms|msc)-", p.name.lower()) else "QP"
            idx[(code, variant, kind)] = p
            continue
        # Fall back to a loose "<code> ... QP/MS" filename.
        m = re.search(r"\b([0-9][A-Z]{2}[0-9]{1,2}|W[A-Z]{2}[0-9]{2})\b", p.name.upper())
        if m:
            kind = "MS" if re.search(r"\bMS\b|mark", p.name, re.I) else "QP"
            idx.setdefault((m.group(1), None, kind), p)
    return idx


def fetch_dir(entry: dict, staging_index: dict) -> tuple[bytes | None, str]:
    for key in ((entry["pearson_code"], entry.get("variant"), entry["kind"]),
                (entry["pearson_code"], None, entry["kind"])):
        p = staging_index.get(key)
        if p:
            return p.read_bytes(), f"staged {p.name}"
    return None, "not present in staging folder"


# ── Publishing ───────────────────────────────────────────────────────────────

def shapes_for(rows: list) -> tuple[str | None, str | None, set, int]:
    """Derive the subject's R2 URL shapes and locate any sessions they can't rebuild.

    `derive_shapes` is all-or-nothing: one legacy row with an old folder name
    (Maths A has two from 2020 oct-nov) disqualifies the whole subject. That is
    right for back-filling old rows and too strict for writing new ones, so we
    keep the shape and return the sessions it fails to reproduce — callers skip
    those sessions and publish the rest.
    """
    qp, ms, _ = derive_shapes(rows)
    bad = set()
    for row in rows:
        for col, shape in (("pdf_url", qp), ("markscheme_pdf_url", ms)):
            if row.get(col) and shape:
                built = fill_shape(shape, row["year"], row["season"], row["paper_number"])
                if built != row[col]:
                    bad.add((row["year"], row["season"]))
    return qp, ms, bad, len(rows)


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
                        region_name="auto", config=Config(retries={"max_attempts": 3}))


def r2_exists(r2, key: str) -> bool:
    try:
        r2.head_object(Bucket=R2_BUCKET, Key=key)
        return True
    except Exception:
        return False


def load_existing(year: int) -> dict:
    """Index every `papers` row for the series: (subject_id, season, paper_number) -> row."""
    rows, offset = [], 0
    while True:
        batch = requests.get(f"{SUPABASE_URL}/rest/v1/papers", headers=H, timeout=60, params={
            "select": "id,subject_id,year,season,paper_number,pdf_url,markscheme_pdf_url",
            "year": f"eq.{year}", "limit": "1000", "offset": str(offset)}).json()
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return {(r["subject_id"], r["season"], str(r["paper_number"])): r for r in rows}


def find_row(existing: dict, entry: dict) -> dict | None:
    return existing.get((entry["subject_id"], entry["season"], str(entry["paper_number"])))


def write_row(existing: dict, row: dict | None, entry: dict, public_url: str) -> str:
    """Patch the NULL column, or insert the row. Keeps `existing` in step so the
    QP and MS of one paper land on a single row within a run."""
    col = "pdf_url" if entry["kind"] == "QP" else "markscheme_pdf_url"
    if row:
        if row.get(col):
            return "row already had a url"
        resp = requests.patch(f"{SUPABASE_URL}/rest/v1/papers", headers={**H, "Content-Type": "application/json"},
                              params={"id": f"eq.{row['id']}", col: "is.null"},
                              json={col: public_url}, timeout=60)
        resp.raise_for_status()
        row[col] = public_url
        return "patched existing row"
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/papers",
                         headers={**H, "Content-Type": "application/json", "Prefer": "return=representation"},
                         json={"subject_id": entry["subject_id"], "year": entry["year"],
                               "season": entry["season"], "paper_number": entry["paper_number"],
                               col: public_url}, timeout=60)
    resp.raise_for_status()
    created = (resp.json() or [{}])[0]
    existing[(entry["subject_id"], entry["season"], str(entry["paper_number"]))] = created
    return "inserted new row"


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_refresh(args) -> None:
    print(f"Querying Pearson's catalogue for the {args.year} series...")
    manifest = build_manifest(args.year)
    out = manifest_path(args.year)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    gated = sum(e["gated"] for e in manifest)
    adapted = sum(e["adapted"] for e in manifest)
    print(f"\n{len(manifest)} QP/MS assets for {args.year} ({gated} still gated, "
          f"{len(manifest) - gated} released; {adapted} are adapted duplicates)")
    print(f"written: {out.relative_to(ROOT)}")


def load_manifest(year: int) -> list[dict]:
    path = manifest_path(year)
    if not path.exists():
        sys.exit(f"no manifest at {path} — run `refresh --year {year}` first")
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_status(args) -> None:
    manifest = annotate(load_manifest(args.year), load_subjects(), args.include_adapted)
    ours = [e for e in manifest if e["subject"] and e["paper_number"]]
    print(f"manifest: {len(manifest)} papers; {len(ours)} map onto subjects we carry")

    live = {}
    if args.probe:
        print("probing live availability (sampling each subject/season)...")
        sample = {}
        for e in ours:
            sample.setdefault((e["subject"], e["season"]), e)
        with httpx.Client(headers=UA, timeout=40, follow_redirects=True) as c:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for key, got in zip(sample, pool.map(lambda e: fetch_pearson(e, c)[0] is not None, sample.values())):
                    live[key] = got

    existing = load_existing(args.year)
    held = defaultdict(lambda: [0, 0])
    for e in ours:
        row = find_row(existing, e)
        col = "pdf_url" if e["kind"] == "QP" else "markscheme_pdf_url"
        held[(e["subject"], e["season"])][0] += 1
        held[(e["subject"], e["season"])][1] += 1 if (row and row.get(col)) else 0

    print(f"\n{'subject':34} {'season':8} {'exist':>6} {'held':>6}" + ("  released" if args.probe else ""))
    tot = [0, 0]
    for key in sorted(held):
        n, h = held[key]
        tot[0] += n
        tot[1] += h
        flag = ("  yes" if live.get(key) else "  gated") if args.probe else ""
        print(f"{key[0]:34} {key[1]:8} {n:6} {h:6}{flag}")
    print(f"{'TOTAL':34} {'':8} {tot[0]:6} {tot[1]:6}")
    print(f"\nmissing: {tot[0] - tot[1]} of {tot[0]} files")

    unmatched = defaultdict(int)
    for e in manifest:
        if not (e["subject"] and e["paper_number"]):
            unmatched[e["pearson_code"]] += 1
    if unmatched:
        print(f"\nnot mapped to any subject we carry ({sum(unmatched.values())} assets): "
              f"{', '.join(sorted(unmatched))}")


def cmd_ingest(args) -> None:
    manifest = annotate(load_manifest(args.year), load_subjects(), args.include_adapted)
    ours = [e for e in manifest if e["subject"] and e["paper_number"]]
    if args.subject:
        ours = [e for e in ours if e["subject"] == args.subject]
    if args.season:
        ours = [e for e in ours if e["season"] == args.season]

    staging_index = {}
    if args.source == "dir":
        if not args.staging:
            sys.exit("--source dir requires --staging <folder>")
        staging = Path(args.staging)
        if not staging.is_dir():
            sys.exit(f"staging folder not found: {staging}")
        staging_index = index_staging(staging)
        print(f"staging folder holds {len(staging_index)} identifiable PDFs")

    by_subject = defaultdict(list)
    for e in ours:
        by_subject[e["subject"]].append(e)

    existing = load_existing(args.year)
    r2 = get_r2() if args.commit else None
    stats = defaultdict(int)
    print(f"\n{len(ours)} candidate files across {len(by_subject)} subjects "
          f"({'COMMIT' if args.commit else 'dry-run'}, source={args.source})\n")

    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as client:
        for subject, entries in sorted(by_subject.items()):
            qp_shape, ms_shape, bad_sessions, _n = shapes_for(fetch_subject_rows(entries[0]["subject_id"]))
            if not (qp_shape and ms_shape):
                print(f"!! {subject}: no R2 URL convention to copy — skipping {len(entries)} files")
                stats["skipped_subject"] += len(entries)
                continue
            entries = [e for e in entries if (e["year"], e["season"]) not in bad_sessions]
            if not entries:
                continue

            print(f"=== {subject}")
            for e in sorted(entries, key=lambda x: (x["season"], x["paper_number"], x["kind"])):
                tag = f"{e['season']:8} {e['paper_number']:8} {e['kind']}"
                row = find_row(existing, e)
                col = "pdf_url" if e["kind"] == "QP" else "markscheme_pdf_url"
                if row and row.get(col):
                    stats["already"] += 1
                    continue

                body, note = (fetch_pearson(e, client) if args.source == "pearson"
                              else fetch_dir(e, staging_index))
                if body is None:
                    print(f"  --    {tag}  {note}")
                    stats["unavailable"] += 1
                    continue

                ok, why = verify_page1(body, e["kind"], e["year"], e["season"], e["pearson_code"])
                if not ok:
                    print(f"  REJECT {tag}  {why}")
                    stats["rejected"] += 1
                    continue

                target = fill_shape(qp_shape if e["kind"] == "QP" else ms_shape,
                                    e["year"], e["season"], e["paper_number"])
                key = r2_key_from_url(target)
                if not args.commit:
                    print(f"  would  {tag}  {why}; {note} -> {key}")
                    stats["would"] += 1
                    continue

                if not r2_exists(r2, key):
                    cleaned, _redactions, _code = clean_and_stamp(body)
                    r2.put_object(Bucket=R2_BUCKET, Key=key, Body=cleaned, ContentType="application/pdf")
                wrote = write_row(existing, row, e, target)
                print(f"  OK     {tag}  {why}; {wrote}")
                stats["published"] += 1

    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    if stats["unavailable"] and args.source == "pearson":
        print(f"\n{stats['unavailable']} files are still behind Pearson's release lock. "
              f"Re-run this command later — it is idempotent and will pick them up.")


def cmd_ingest_urls(args) -> None:
    """Ingest a list of direct PDF links, whatever site they were saved from.

    Nothing is crawled or discovered here: the caller supplies the URLs. Each
    file is identified from its own cover page, so a wrong or mislabelled link
    is reported and skipped rather than filed under the wrong paper.
    """
    urls = [ln.strip() for ln in Path(args.urls).read_text(encoding="utf-8").splitlines()]
    urls = [u for u in urls if u and not u.startswith("#")]
    if not urls:
        sys.exit(f"no URLs in {args.urls}")

    by_code = load_subjects()
    r2 = get_r2() if args.commit else None
    shapes: dict[str, tuple] = {}
    existing_by_year: dict[int, dict] = {}
    adapted_by_year: dict[int, set] = {}
    # Papers claimed earlier in this run. Without this a dry-run would count an
    # adapted paper and its plain sibling as two publishes, because nothing is
    # written for the second to collide with.
    claimed: set = set()
    stats = defaultdict(int)
    print(f"{len(urls)} URLs ({'COMMIT' if args.commit else 'dry-run'})\n")

    cache_dir = Path(args.cache) if args.cache else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"cache: {cache_dir}")

    headers = {**UA, "Accept": "application/pdf,*/*", "Accept-Language": "en-US,en;q=0.9"}
    if args.referer:
        headers["Referer"] = args.referer

    with httpx.Client(headers=headers, timeout=90, follow_redirects=True) as client:
        for url in urls:
            label = url.rsplit("/", 1)[-1][:58]
            # A cache makes a dry-run and the commit that follows it cost one
            # download rather than two, which matters when the list is hundreds
            # of files long and they are somebody else's bytes.
            cached = None
            if cache_dir:
                import hashlib
                cached = cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
            if cached and cached.exists():
                body, note = cached.read_bytes(), f"cached {cached.stat().st_size // 1024}KB"
            else:
                body, note = fetch_url(url, client)
                if body is not None and cached:
                    cached.write_bytes(body)
            if body is None:
                print(f"  SKIP   {label}  {note}")
                stats["unavailable"] += 1
                continue

            ident, why = identify_pdf(body)
            if ident is None:
                print(f"  SKIP   {label}  {why}")
                stats["unidentified"] += 1
                continue

            # Pearson publishes an adapted paper beside some plain ones
            # ("WBI11/01A" next to "WBI11/01") — a different, shorter document.
            # Our catalogue carries the plain paper, and the manifest already
            # knows which is which, so let it decide rather than guessing from
            # the variant's spelling (IGCSE "2A"/"1C" are genuine papers).
            yr = ident["year"]
            if yr not in adapted_by_year:
                try:
                    adapted_by_year[yr] = {
                        (e["pearson_code"], e["variant"], e["season"], e["kind"])
                        for e in load_manifest(yr) if e.get("adapted")}
                except SystemExit:
                    adapted_by_year[yr] = set()
            akey = (ident["pearson_code"], ident["variant"], ident["season"], ident["kind"])
            if akey in adapted_by_year[yr]:
                print(f"  ~      {label}  adapted variant "
                      f"({ident['pearson_code']}/{ident['variant']}); we carry the plain paper")
                stats["adapted"] += 1
                continue

            subject = match_subject(ident, by_code)
            if not subject:
                print(f"  SKIP   {label}  {ident['pearson_code']}: no subject we carry")
                stats["no_subject"] += 1
                continue
            paper_number = paper_number_for(ident["family"], ident["pearson_code"],
                                            ident["variant"], None)
            if not paper_number:
                print(f"  SKIP   {label}  cannot map {ident['pearson_code']}/{ident['variant']}")
                stats["no_subject"] += 1
                continue

            entry = {**ident, "subject": subject["name"], "subject_id": subject["id"],
                     "paper_number": paper_number}
            tag = f"{subject['name']} {ident['year']} {ident['season']} {paper_number} {ident['kind']}"

            if subject["id"] not in shapes:
                shapes[subject["id"]] = shapes_for(fetch_subject_rows(subject["id"]))
            qp_shape, ms_shape, bad_sessions, _n = shapes[subject["id"]]
            if not (qp_shape and ms_shape):
                print(f"  SKIP   {tag}  no R2 URL convention to copy")
                stats["skipped_subject"] += 1
                continue
            if (ident["year"], ident["season"]) in bad_sessions:
                print(f"  SKIP   {tag}  this session's stored URLs use a non-standard key")
                stats["skipped_subject"] += 1
                continue

            if ident["year"] not in existing_by_year:
                existing_by_year[ident["year"]] = load_existing(ident["year"])
            existing = existing_by_year[ident["year"]]
            row = find_row(existing, entry)
            col = "pdf_url" if ident["kind"] == "QP" else "markscheme_pdf_url"
            claim = (subject["id"], ident["year"], ident["season"], paper_number, col)
            if row and row.get(col):
                print(f"  ~      {tag}  already held")
                stats["already"] += 1
                continue
            if claim in claimed:
                print(f"  ~      {tag}  a file for this slot was already taken this run")
                stats["duplicate"] += 1
                continue

            target = fill_shape(qp_shape if ident["kind"] == "QP" else ms_shape,
                                ident["year"], ident["season"], paper_number)
            key = r2_key_from_url(target)
            if not args.commit:
                claimed.add(claim)
                print(f"  would  {tag}  ({note}) -> {key}")
                stats["would"] += 1
                continue
            claimed.add(claim)

            if not r2_exists(r2, key):
                cleaned, redactions, _ = clean_and_stamp(body)
                r2.put_object(Bucket=R2_BUCKET, Key=key, Body=cleaned, ContentType="application/pdf")
                note = f"{note}, {redactions} watermark redactions"
            wrote = write_row(existing, row, entry, target)
            print(f"  OK     {tag}  ({note}); {wrote}")
            stats["published"] += 1

    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(stats.items())))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("refresh", help="rebuild the manifest from Pearson's catalogue")
    p.add_argument("--year", type=int, default=2026)
    p.set_defaults(fn=cmd_refresh)

    p = sub.add_parser("status", help="manifest vs what we hold")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--probe", action="store_true", help="also check live Pearson availability")
    p.add_argument("--include-adapted", action="store_true", help="include Pearson's adapted -a papers")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("ingest", help="acquire and publish everything obtainable")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--source", choices=("pearson", "dir"), default="pearson")
    p.add_argument("--staging", default=None, help="folder of PDFs for --source dir")
    p.add_argument("--subject", default=None)
    p.add_argument("--season", default=None, choices=("jan", "may-jun", "oct-nov"))
    p.add_argument("--include-adapted", action="store_true", help="include Pearson's adapted -a papers")
    p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("ingest-urls", help="ingest a supplied list of direct PDF links")
    p.add_argument("--urls", required=True, help="text file, one PDF URL per line")
    p.add_argument("--referer", default=None, help="send a Referer header with each request")
    p.add_argument("--cache", default=None,
                   help="directory to cache downloads in, so re-runs do not refetch")
    p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_ingest_urls)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
