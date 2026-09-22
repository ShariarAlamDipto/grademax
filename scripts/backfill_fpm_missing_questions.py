#!/usr/bin/env python3
"""Backfill Further Pure Maths (4PM1) questions that live in R2 but have no `pages` row.

The segmentation pipeline uploaded 833 question PDFs to
`subjects/Further_Pure_Mathematics/pages/<folder>/qN.pdf`, but only 735 of them
were ever indexed in Postgres. The test builder and the worksheet generator both
read `pages` (filtered on `is_question` + `qp_page_url`), so the un-indexed
questions are invisible to users even though the files serve fine.

This script closes that gap. It never re-segments and never uploads: it reads R2,
diffs against the database, and inserts the missing rows.

Three classes of gap are handled:

  1. 2020 Oct-Nov series (4 papers, 40 questions). The `papers` rows exist but
     hold zero pages. The segmentation folders are labelled `2020_Jun_*`; the
     content was verified to be the Oct-Nov 2020 series (Edexcel reused the
     June 2020 papers, which print "June 2020" on the cover), so the folders map
     onto the existing `2020 / oct-nov` rows.
  2. 2017 Oct-Nov (2 papers, 19 questions). No `papers` row exists at all — this
     script creates them. `pdf_url` / `markscheme_pdf_url` stay NULL because the
     stamped full-paper PDFs are not in the R2 archive; every public past-papers
     query filters on `pdf_url.not.is.null,markscheme_pdf_url.not.is.null`, so
     the rows stay invisible on the past-papers site while their questions
     become usable in the tools.
  3. ~39 individual questions scattered across papers that are otherwise indexed.

Usage:
    python scripts/backfill_fpm_missing_questions.py              # dry run
    python scripts/backfill_fpm_missing_questions.py --execute    # write

The script is idempotent: anything already present in `pages` is skipped, so it
is safe to re-run after a partial failure.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import boto3
import fitz  # PyMuPDF
import yaml
from dotenv import load_dotenv
from supabase import Client, create_client

sys.path.append(str(Path(__file__).parent))
from mistral_classifier import MistralTopicClassifier  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENV_PATH = REPO_ROOT / ".env.local"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "Further Pure Maths Processed"
TOPICS_YAML = REPO_ROOT / "classification" / "further_pure_maths_topics.yaml"

SUBJECT_CODE = "4PM1"
R2_PAGES_PREFIX = "subjects/Further_Pure_Mathematics/pages/"
FALLBACK_PUBLIC_BASE = "https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev"

FOLDER_RE = re.compile(r"^(\d{4})_(Jan|Jun|Nov|Specimen)_(\d+R?)P$")
OBJECT_RE = re.compile(re.escape(R2_PAGES_PREFIX) + r"([^/]+)/q(\d+)(_ms)?\.pdf$")
URL_RE = re.compile(r"/pages/([^/]+)/q(\d+)\.pdf$")

SEASON_BY_FOLDER_TOKEN = {
    "Jan": "jan",
    "Jun": "may-jun",
    "Nov": "oct-nov",
    "Specimen": "specimen",
}

# Folders whose label does not match the session the papers were actually sat in.
# Verified by text-matching the segments against the archived Oct-Nov 2020 QPs.
SEASON_OVERRIDES = {
    "2020_Jun_1P": "oct-nov",
    "2020_Jun_1RP": "oct-nov",
    "2020_Jun_2P": "oct-nov",
    "2020_Jun_2RP": "oct-nov",
}

TEXT_EXCERPT_CHARS = 500


@dataclass(frozen=True)
class PaperKey:
    """Identity of a paper row: (year, season, paper_number)."""

    year: int
    season: str
    paper_number: str


@dataclass(frozen=True)
class MissingQuestion:
    """One question present in R2 but absent from `pages`."""

    folder: str
    question: int
    paper_key: PaperKey
    qp_url: str
    ms_url: str | None
    local_pdf: Path


def load_env() -> None:
    if not ENV_PATH.exists():
        sys.exit(f"[FATAL] {ENV_PATH} not found")
    load_dotenv(ENV_PATH)


def new_supabase() -> Client:
    """A fresh client per call — the pooled HTTP/2 connection drops on reuse."""
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("[FATAL] Missing Supabase credentials in .env.local")
    return create_client(url, key)


def with_retry(fn, attempts: int = 4, delay: float = 2.0):
    """Supabase over HTTP/2 intermittently drops connections; retry transparently."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn(new_supabase())
        except Exception as exc:  # noqa: BLE001 - transport errors are opaque
            last = exc
            if attempt < attempts - 1:
                time.sleep(delay)
    raise RuntimeError(f"Supabase call failed after {attempts} attempts: {last}")


def parse_folder(folder: str) -> PaperKey | None:
    match = FOLDER_RE.match(folder)
    if not match:
        return None
    year, token, paper = match.group(1), match.group(2), match.group(3)
    season = SEASON_OVERRIDES.get(folder) or SEASON_BY_FOLDER_TOKEN[token]
    return PaperKey(year=int(year), season=season, paper_number=paper)


def list_r2_pages() -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    """Return (question PDFs, mark scheme PDFs) keyed by segmentation folder."""
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )
    bucket = os.getenv("R2_BUCKET_NAME")
    questions: dict[str, set[int]] = defaultdict(set)
    markschemes: dict[str, set[int]] = defaultdict(set)

    token: str | None = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": R2_PAGES_PREFIX, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        for obj in response.get("Contents", []):
            match = OBJECT_RE.match(obj["Key"])
            if not match:
                continue
            folder, number, is_ms = match.group(1), int(match.group(2)), match.group(3)
            (markschemes if is_ms else questions)[folder].add(number)
        if not response.get("IsTruncated"):
            break
        token = response["NextContinuationToken"]

    return dict(questions), dict(markschemes)


def fetch_subject_id() -> str:
    rows = with_retry(
        lambda db: db.table("subjects").select("id").eq("code", SUBJECT_CODE).execute().data
    )
    if not rows:
        sys.exit(f"[FATAL] Subject {SUBJECT_CODE} not found")
    return rows[0]["id"]


def fetch_papers(subject_id: str) -> dict[PaperKey, str]:
    rows = with_retry(
        lambda db: db.table("papers")
        .select("id,year,season,paper_number")
        .eq("subject_id", subject_id)
        .execute()
        .data
    )
    return {
        PaperKey(int(r["year"]), str(r["season"]), str(r["paper_number"])): r["id"]
        for r in rows
    }


def fetch_indexed_questions(paper_ids: Iterable[str]) -> dict[str, set[int]]:
    """Map segmentation folder -> question numbers that already have a `pages` row."""
    ids = list(paper_ids)
    indexed: dict[str, set[int]] = defaultdict(set)
    for start in range(0, len(ids), 40):
        chunk = ids[start : start + 40]
        offset = 0
        while True:
            rows = with_retry(
                lambda db, c=chunk, o=offset: db.table("pages")
                .select("qp_page_url")
                .in_("paper_id", c)
                .range(o, o + 999)
                .execute()
                .data
            )
            for row in rows:
                match = URL_RE.search(row.get("qp_page_url") or "")
                if match:
                    indexed[match.group(1)].add(int(match.group(2)))
            if len(rows) < 1000:
                break
            offset += 1000
    return dict(indexed)


def resolve_public_base() -> str:
    """Derive the R2 public host from an existing row so the URL style stays uniform."""
    rows = with_retry(
        lambda db: db.table("pages")
        .select("qp_page_url")
        .like("qp_page_url", f"%{R2_PAGES_PREFIX}%")
        .limit(1)
        .execute()
        .data
    )
    if rows and rows[0].get("qp_page_url"):
        return rows[0]["qp_page_url"].split(f"/{R2_PAGES_PREFIX}")[0]
    return FALLBACK_PUBLIC_BASE


def build_plan(
    r2_questions: dict[str, set[int]],
    r2_markschemes: dict[str, set[int]],
    indexed: dict[str, set[int]],
    public_base: str,
) -> list[MissingQuestion]:
    plan: list[MissingQuestion] = []
    for folder in sorted(r2_questions):
        paper_key = parse_folder(folder)
        if paper_key is None:
            print(f"   [SKIP] unparseable folder name: {folder}")
            continue
        missing = sorted(r2_questions[folder] - indexed.get(folder, set()))
        for number in missing:
            local_pdf = PROCESSED_DIR / folder / "pages" / f"q{number}.pdf"
            has_ms = number in r2_markschemes.get(folder, set())
            base = f"{public_base}/{R2_PAGES_PREFIX}{folder}"
            plan.append(
                MissingQuestion(
                    folder=folder,
                    question=number,
                    paper_key=paper_key,
                    qp_url=f"{base}/q{number}.pdf",
                    ms_url=f"{base}/q{number}_ms.pdf" if has_ms else None,
                    local_pdf=local_pdf,
                )
            )
    return plan


def read_pdf(item: MissingQuestion) -> tuple[str, int]:
    """Return (extracted text, page count) for a segment, preferring the local copy."""
    if item.local_pdf.exists():
        doc = fitz.open(item.local_pdf)
    else:
        import urllib.request

        with urllib.request.urlopen(item.qp_url, timeout=60) as response:
            doc = fitz.open(stream=response.read(), filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc), len(doc)
    finally:
        doc.close()


class TopicNormaliser:
    """Maps whatever the LLM returns onto the numeric ids stored in `pages.topics`.

    The YAML gives each topic a numeric `id` ("1".."10") and a mnemonic `code`
    ("LOGS", "QUAD", ...). `pages.topics` stores the numeric id, but the model
    frequently answers with the mnemonic, so both are accepted.
    """

    def __init__(self, topics_yaml: Path) -> None:
        data = yaml.safe_load(topics_yaml.read_text(encoding="utf-8"))
        self.valid_ids = {str(t["id"]) for t in data["topics"]}
        self.by_code = {str(t["code"]).upper(): str(t["id"]) for t in data["topics"]}

    def normalise(self, topic: object) -> str | None:
        text = str(topic).strip()
        if text in self.valid_ids:
            return text
        if text.upper() in self.by_code:
            return self.by_code[text.upper()]
        leading = re.match(r"^(\d+)", text)
        if leading and leading.group(1) in self.valid_ids:
            return leading.group(1)
        return None


def ensure_paper_rows(
    plan: list[MissingQuestion], papers: dict[PaperKey, str], subject_id: str, execute: bool
) -> dict[PaperKey, str]:
    """Create `papers` rows for sessions the plan needs but the database lacks."""
    needed = {item.paper_key for item in plan}
    missing = sorted(needed - set(papers), key=lambda k: (k.year, k.season, k.paper_number))
    if not missing:
        return papers

    print(f"\n   {len(missing)} paper row(s) must be created:")
    created = dict(papers)
    for key in missing:
        print(f"      + {key.year} {key.season} paper {key.paper_number}")
        if not execute:
            continue
        row = with_retry(
            lambda db, k=key: db.table("papers")
            .insert(
                {
                    "subject_id": subject_id,
                    "year": k.year,
                    "season": k.season,
                    "paper_number": k.paper_number,
                    "pdf_url": None,
                    "markscheme_pdf_url": None,
                }
            )
            .execute()
            .data
        )
        created[key] = row[0]["id"]
    return created


def backfill(plan: list[MissingQuestion], papers: dict[PaperKey, str], execute: bool) -> None:
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(TOPICS_YAML), groq_api_key=os.getenv("GROQ_API_KEY")
    )
    normaliser = TopicNormaliser(TOPICS_YAML)

    inserted = 0
    fallbacks: list[str] = []
    failures: list[str] = []

    for index, item in enumerate(plan, start=1):
        label = f"{item.folder} q{item.question}"
        paper_id = papers.get(item.paper_key)
        if not paper_id:
            failures.append(f"{label}: no paper row")
            continue

        try:
            text, page_count = read_pdf(item)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append(f"{label}: could not read PDF ({exc})")
            continue

        result = classifier.classify(text, f"Q{item.question}")
        topic = normaliser.normalise(result.topic) if result else None
        if topic is None:
            topic = "1"
            fallbacks.append(label)

        row = {
            "paper_id": paper_id,
            "page_number": item.question,
            "question_number": str(item.question),
            "topics": [topic],
            "difficulty": result.difficulty if result else "medium",
            "confidence": float(result.confidence) if result else 0.0,
            "qp_page_url": item.qp_url,
            "ms_page_url": item.ms_url,
            "is_question": True,
            "has_diagram": False,
            "page_count": page_count,
            "text_excerpt": text[:TEXT_EXCERPT_CHARS],
        }

        marker = "" if item.ms_url else "  (no mark scheme)"
        print(
            f"   [{index:3d}/{len(plan)}] {label:24s} topic={topic:<2s} "
            f"{row['difficulty']:<6s} conf={row['confidence']:.2f}{marker}",
            flush=True,
        )

        if execute:
            try:
                with_retry(lambda db, r=row: db.table("pages").insert(r).execute().data)
                inserted += 1
            except Exception as exc:  # noqa: BLE001 - report and continue
                failures.append(f"{label}: insert failed ({exc})")

    print("\n" + "=" * 78)
    print(f"   planned      : {len(plan)}")
    print(f"   inserted     : {inserted}" if execute else "   inserted     : 0 (dry run)")
    print(f"   topic fallback to '1' (needs review): {len(fallbacks)}")
    for label in fallbacks:
        print(f"      - {label}")
    if failures:
        print(f"   failures     : {len(failures)}")
        for failure in failures:
            print(f"      ! {failure}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="write to Supabase (without this flag the script only reports)",
    )
    args = parser.parse_args()

    load_env()
    mode = "EXECUTE" if args.execute else "DRY RUN"
    print("=" * 78)
    print(f"  FPM (4PM1) missing-question backfill  [{mode}]")
    print("=" * 78)

    subject_id = fetch_subject_id()
    papers = fetch_papers(subject_id)
    r2_questions, r2_markschemes = list_r2_pages()
    indexed = fetch_indexed_questions(papers.values())

    total_r2 = sum(len(v) for v in r2_questions.values())
    total_indexed = sum(len(v) for v in indexed.values())
    print(f"\n   subject {SUBJECT_CODE}: {len(papers)} paper rows")
    print(f"   question PDFs in R2 : {total_r2}")
    print(f"   already indexed     : {total_indexed}")

    public_base = resolve_public_base()
    plan = build_plan(r2_questions, r2_markschemes, indexed, public_base)
    print(f"   to backfill         : {len(plan)}")

    if not plan:
        print("\n   Nothing to do — every R2 question already has a row.")
        return

    by_folder: dict[str, list[int]] = defaultdict(list)
    for item in plan:
        by_folder[item.folder].append(item.question)
    print()
    for folder in sorted(by_folder):
        numbers = ",".join(f"q{n}" for n in sorted(by_folder[folder]))
        print(f"      {folder:20s} {numbers}")

    papers = ensure_paper_rows(plan, papers, subject_id, args.execute)

    missing_local = [i for i in plan if not i.local_pdf.exists()]
    if missing_local:
        print(f"\n   {len(missing_local)} segment(s) absent locally — will read from R2")

    if not args.execute:
        print("\n   Dry run complete. Re-run with --execute to write these rows.")
        return

    print("\n   Classifying and inserting...\n")
    backfill(plan, papers, execute=True)


if __name__ == "__main__":
    main()
