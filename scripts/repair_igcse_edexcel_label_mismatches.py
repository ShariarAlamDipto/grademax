#!/usr/bin/env python3
"""Put the right document in every Edexcel IGCSE slot whose label the audit
contradicts.

Two sources, tried in order:

  1. A **local twin** -- a file already in the same session folder whose own cover
     proves it is exactly the paper this slot promises. Most of the damage is a
     slot holding a neighbour's paper while the correct document sits beside it
     under its other Edexcel spelling (`Paper_1` vs `Paper_1F`, `Paper_2` vs
     `Paper_2C`). Copying locally needs no network and the source is already
     cover-verified, so it is always preferred.
  2. **Pearson's official catalogue**, reached through their public Algolia index.
     Used when the archive simply does not contain the promised paper. A wrong
     Pearson path answers HTTP 200 with `text/html`, so content-type and the
     `%PDF` magic are both checked, and the download must then pass the same
     cover test as any other candidate.

Nothing is written on the strength of a filename or a PMT watermark: the
replacement must positively identify itself as the right subject, paper, session
and document type before it may overwrite anything.

The R2 key is read from the `papers` row, never constructed. Key shapes are not
uniform -- ICT lives at `ICT/<year>/...` with no `igcse/` prefix, Business at
`igcse/business/`, Mathematics A at `igcse/maths-a/` -- so a built key would
silently upload beside the live object and leave production serving the bad file.

Filenames never change, so no `papers` row needs patching.

Dry-run by default; --commit writes the archive, --upload also pushes to R2.

Usage:
    python -X utf8 scripts/repair_igcse_edexcel_label_mismatches.py
    python -X utf8 scripts/repair_igcse_edexcel_label_mismatches.py --subject Physics
    python -X utf8 scripts/repair_igcse_edexcel_label_mismatches.py --all --commit --upload
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from source_m1_question_papers import clean_and_stamp, verify  # noqa: E402
from audit_igcse_edexcel_labels import (  # noqa: E402
    ARCHIVE_ROOT, FILENAME_RE, WATERMARK_RE, accepted_codes, inspect,
    is_convention, variants_compatible,
)
from fix_igcse_edexcel_mislabelled_files import (  # noqa: E402
    PEARSON_SLUG, UA, pearson_catalog, subject_paper_letters, verify_replacement,
    wanted_codes,
)

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
AUDIT_JSON = REPO_ROOT / "data" / "analysis" / "igcse_edexcel_label_audit.json"
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "igcse_label_mismatches"

FOLDER = {
    "Accounting": "Accounting", "Bangla": "Bangla", "Biology": "Biology",
    "Business Studies": "Business_Studies", "Chemistry": "Chemistry",
    "Commerce": "Commerce", "Computer Science": "Computer_Science",
    "Economics": "Economics", "English Language A": "English_A",
    "English Language B": "English_B", "Further Pure Mathematics": "Further_Pure_Maths",
    "Geography": "Geography", "Human Biology": "Human_Biology", "ICT": "ICT",
    "Mathematics A": "Mathematics_A", "Mathematics B": "Mathematics_B",
    "Mechanics 1": "Mechanics_1", "Physics": "Physics",
}


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def fetch_all(path: str) -> list[dict]:
    out: list[dict] = []
    off = 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}&limit=1000&offset={off}",
                         headers=H, timeout=60)
        r.raise_for_status()
        batch = r.json()
        out += batch
        if len(batch) < 1000:
            return out
        off += 1000


def live_keys() -> dict[str, str]:
    """archive filename -> the exact R2 key production serves it from."""
    out: dict[str, str] = {}
    for s in fetch_all("subjects?select=id,name,level"):
        if (s.get("level") or "").lower() != "igcse" or s["name"].startswith("Cambridge"):
            continue
        if s["name"] not in FOLDER:
            continue
        for r in fetch_all(f"papers?select=pdf_url,markscheme_pdf_url"
                           f"&subject_id=eq.{s['id']}"):
            for col in ("pdf_url", "markscheme_pdf_url"):
                m = re.search(r"\.r2\.dev/(.+)$", r.get(col) or "")
                if m:
                    out[m.group(1).split("/")[-1]] = m.group(1)
    return out


def uses_tiers(subject: str) -> bool:
    files = (ARCHIVE_ROOT / subject).rglob("*.pdf")
    return any((m := FILENAME_RE.match(f.name)) and re.search(r"[FH]", m.group("paper").upper())
               for f in files)


def head_text(body: bytes, pages: int = 3) -> str:
    """Front-matter text with PMT/GradeMax provenance strips removed."""
    with fitz.open(stream=body, filetype="pdf") as doc:
        raw = " ".join(doc[i].get_text() for i in range(min(pages, doc.page_count)))
    return WATERMARK_RE.sub(" ", " ".join(raw.split()))


def find_local_twin(subject: str, year: str, season: str, paper: str, kind: str,
                    exclude: Path, tiers: bool) -> tuple[Path, str] | None:
    """A file in the same session whose cover proves it is the promised paper."""
    folder = ARCHIVE_ROOT / subject / year / season
    if not folder.is_dir():
        return None
    for cand in sorted(folder.glob("*.pdf")):
        if cand == exclude:
            continue
        m = FILENAME_RE.match(cand.name)
        if not m or m.group("kind") != kind:
            continue
        row = inspect((str(cand.relative_to(REPO_ROOT)), subject, tiers))
        if row["status"] not in ("OK", "CONVENTION"):
            continue
        found = row.get("found")
        if not found:
            continue
        ok = variants_compatible(paper, found, tiers)
        if ok is not True and not is_convention(subject, paper, found):
            continue
        # `status` being OK/CONVENTION already means this candidate's own cover
        # agrees with the session folder it sits in, which is the session we are
        # filling -- so no separate session check is needed here.
        return cand, f"{cand.name.split('_Paper_')[-1][:-4]} cover={found} {row['evidence']}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()

    audit = json.loads(AUDIT_JSON.read_text("utf-8"))
    bad = [r for r in audit if r["status"] == "MISMATCH"]
    if args.subject:
        bad = [r for r in bad if r["subject"].lower() == args.subject.lower()]

    keys = live_keys()
    client = r2_client() if args.upload else None
    catalogs: dict[str, dict] = {}
    tier_cache: dict[str, bool] = {}
    fixed = skipped = unserved = 0

    for r in sorted(bad, key=lambda x: x["file"]):
        subject = r["subject"]
        path = REPO_ROOT / r["file"]
        fn = FILENAME_RE.match(path.name)
        if not fn or not path.exists():
            continue
        key = keys.get(path.name)
        tag = f"{subject:<17}{r['slot']:<32}"
        if not key:
            print(f"{tag} SKIP: not served (no papers row)")
            unserved += 1
            continue

        year, season = fn.group("year"), path.parent.name
        paper, kind = fn.group("paper").upper(), fn.group("kind")
        tiers = tier_cache.setdefault(subject, uses_tiers(subject))

        body = why = None
        twin = find_local_twin(subject, year, season, paper, kind, path, tiers)
        if twin:
            body = twin[0].read_bytes()
            why = f"local twin {twin[1]}"
        else:
            slug = PEARSON_SLUG.get(subject)
            if not slug:
                print(f"{tag} NO SOURCE: no local twin; no Pearson catalogue for {subject}")
                skipped += 1
                continue
            if slug not in catalogs:
                catalogs[slug] = pearson_catalog(slug)
            catalog = catalogs[slug]
            letters = subject_paper_letters([x for x in audit if x["subject"] == subject])
            url = want = None
            for cand in wanted_codes(paper, r.get("found"), letters):
                if (year, season, cand, kind) in catalog:
                    want, url = cand, catalog[(year, season, cand, kind)]
                    break
            if not url:
                print(f"{tag} NO SOURCE: no local twin; Pearson has no {year}/{season} "
                      f"{paper} {kind}")
                skipped += 1
                continue
            resp = requests.get(url, headers=UA, timeout=120)
            time.sleep(1.0)
            ctype = resp.headers.get("content-type", "").lower()
            if resp.status_code != 200 or resp.content[:4] != b"%PDF" or "html" in ctype:
                print(f"{tag} SKIP: not a PDF (http {resp.status_code}, {ctype[:20]})")
                skipped += 1
                continue
            ok, detail = verify_replacement(resp.content, want, year, season, kind, url)
            if not ok:
                print(f"{tag} REJECTED: {detail}")
                skipped += 1
                continue
            body = resp.content
            why = f"Pearson {url.split('/')[-1]} ({detail})"

        # Final gate: the bytes we are about to install must name this subject.
        # This is what catches the worst defect class -- a Physics slot holding a
        # Chemistry or English mark scheme.
        codes = accepted_codes(subject)
        seen = set(re.findall(r"4[A-Z]{2}[01]", head_text(body)))
        if codes and seen and not any(c.startswith(codes) for c in seen):
            print(f"{tag} REJECTED: replacement names {sorted(seen)}, not {codes}")
            skipped += 1
            continue

        if not args.commit:
            print(f"{tag} [DRY] <- {why}")
            fixed += 1
            continue

        cleaned, _ = clean_and_stamp(body)
        pmt_gone, gm = verify(cleaned)
        if not (pmt_gone and gm):
            print(f"{tag} REJECTED: stamp check (pmt_gone={pmt_gone}, grademax={gm})")
            skipped += 1
            continue
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(QUARANTINE / path.name))
        path.write_bytes(cleaned)
        print(f"{tag} FIXED <- {why}")
        fixed += 1
        if args.upload:
            try:
                client.put_object(Bucket=R2_BUCKET, Key=key, Body=cleaned,
                                  ContentType="application/pdf")
                print(f"{' ' * 49}uploaded -> {key}")
            except Exception as exc:  # noqa: BLE001
                print(f"{' ' * 49}R2 upload FAILED: {exc}")

    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: fixed={fixed} "
          f"skipped={skipped} not-served={unserved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
