"""
The full question paper and mark scheme behind every live `papers` row, on disk.

The live per-question segments are what is broken; the whole-paper PDFs they
were cut from are what the content-pairing audit already checked and repaired
(see scripts/audit_qp_ms_content_pairing.py). So every rebuild starts here:
download each paper's QP and MS once, by direct R2 read, into

    data/analysis/live_rebuild/<CODE>/sources/<year>_<season>_P<n>_{qp,ms}.pdf
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parents[2]
REBUILD_DIR = ROOT / "data" / "analysis" / "live_rebuild"


@dataclass(frozen=True)
class LivePaper:
    paper_id: str
    year: int
    season: str          # "jan" | "may-jun" | "oct-nov" | "specimen"
    paper_number: str    # "1" | "1R" | "2" | "2R"
    qp_url: str | None
    ms_url: str | None
    qp_path: Path | None
    ms_path: Path | None

    @property
    def key(self) -> str:
        return f"{self.year}_{self.season}_P{self.paper_number}"


def supabase_client():
    load_dotenv(ROOT / ".env.local")
    return create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                         os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def fetch_rows(query) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        chunk = query(offset).execute().data or []
        rows.extend(chunk)
        if len(chunk) < 1000:
            return rows
        offset += 1000


def subject_id(sb, code: str) -> str:
    rows = sb.table("subjects").select("id").eq("code", code).execute().data
    if not rows:
        raise SystemExit(f"no subject row for {code}")
    return rows[0]["id"]


def r2_reader():
    """(get_bytes(url), public_prefix) using the same client as the ingest scripts."""
    load_dotenv(ROOT / ".env.local")
    sys.path.insert(0, str(ROOT / "scripts"))
    import ingest_2026_papers as ing  # noqa: PLC0415 -- needs env loaded first

    r2 = ing.get_r2()
    prefix = ing.R2_PUBLIC_URL + "/"

    def get_bytes(url: str) -> bytes | None:
        if not url or not url.startswith(prefix):
            return None
        return r2.get_object(Bucket=ing.R2_BUCKET, Key=url[len(prefix):])["Body"].read()

    return get_bytes, prefix


def load_live_papers(code: str, *, refresh: bool = False) -> list[LivePaper]:
    sb = supabase_client()
    sid = subject_id(sb, code)
    rows = fetch_rows(lambda o: sb.table("papers")
                      .select("id,year,season,paper_number,pdf_url,markscheme_pdf_url")
                      .eq("subject_id", sid).range(o, o + 999))
    out_dir = REBUILD_DIR / code / "sources"
    out_dir.mkdir(parents=True, exist_ok=True)
    get_bytes, _ = r2_reader()

    def one(row: dict) -> LivePaper:
        stem = f"{row['year']}_{row['season']}_P{row['paper_number']}"
        paths: list[Path | None] = []
        for url, kind in ((row["pdf_url"], "qp"), (row["markscheme_pdf_url"], "ms")):
            path = out_dir / f"{stem}_{kind}.pdf"
            if url and (refresh or not path.is_file()):
                try:
                    data = get_bytes(url)
                except Exception:  # noqa: BLE001 -- reported as a missing source
                    data = None
                if data:
                    path.write_bytes(data)
            paths.append(path if path.is_file() else None)
        return LivePaper(row["id"], row["year"], row["season"], str(row["paper_number"]),
                         row["pdf_url"], row["markscheme_pdf_url"], paths[0], paths[1])

    with ThreadPoolExecutor(12) as pool:
        papers = list(pool.map(one, rows))
    return sorted(papers, key=lambda p: (p.year, p.season, p.paper_number))
