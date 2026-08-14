#!/usr/bin/env python3
"""Fix the 2020 session for Chemistry and Mathematics A.

These two were held back from `fix_igcse_edexcel_2020_phantom_session.py` because
their 2020 data is tangled in a way the bulk pass would have mishandled.

Chemistry 2020
    `oct-nov` rows exist for 1C/1CR/2C/2CR but carry **no question paper** at all;
    the only copies live in the phantom `may-jun` session.

Mathematics A 2020
    `oct-nov` is half right and half wrong. The bare-named rows (1/1R/2/2R) hold
    the correct November papers but 1 and 2 have no mark scheme; the tier-named
    rows (1F/1FR/2F/2FR) hold the correct November mark schemes but their question
    papers are the **January 2020** papers (P59752A, P58398A, P59753A, P58428A).

Both subjects also list every paper twice under two naming schemes (Chemistry
`1`==`1C`, Mathematics A `1`==`1F`), which is a separate duplicate-listing defect
and is NOT addressed here -- this script only makes every 2020 row point at the
correct November 2020 document, then removes the phantom `may-jun` session.

Method: the phantom `may-jun` folder happens to hold the complete, correct
November 2020 set (that is precisely why it was duplicated). So we index it by the
paper code printed on each cover, then point every `oct-nov` row at the document
matching its own paper code -- replacing wrong files and filling empty slots
alike. Every write is gated on the cover page.

Dry-run by default; --commit to write. Backs up to
`data/quarantine/igcse_2020_phantom_session/`.

Usage:
    python -X utf8 scripts/fix_chemistry_mathsa_2020_session.py
    python -X utf8 scripts/fix_chemistry_mathsa_2020_session.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
R2_PUBLIC = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL")
             or "https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev").rstrip("/")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")

ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE"
BACKUP = REPO_ROOT / "data" / "quarantine" / "igcse_2020_phantom_session"

YEAR = "2020"
MS_RE = re.compile(r"mark scheme|marking scheme", re.I)
SESSION_RE = re.compile(r"\b(January|February|March|May|June|Summer|October|November|Winter)\s+(20\d{2})\b", re.I)
PAPER_RE = re.compile(r"\bPAPER\s*:?\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])", re.I)
REF_RE = re.compile(r"\b4[A-Z]{2}[01]\s*/\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])")

# subject -> (archive folder, paper_number -> canonical cover paper code)
SUBJECTS = {
    "Chemistry": ("Chemistry", {
        "1": "1C", "1C": "1C", "1R": "1CR", "1CR": "1CR",
        "2": "2C", "2C": "2C", "2R": "2CR", "2CR": "2CR"}),
    "Mathematics A": ("Mathematics_A", {
        "1": "1F", "1F": "1F", "1R": "1FR", "1FR": "1FR",
        "2": "2F", "2F": "2F", "2R": "2FR", "2FR": "2FR"}),
}


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def key_of(url):
    m = re.search(r"\.r2\.dev/(.+)$", url or "")
    return m.group(1) if m else None


def identify(body: bytes) -> dict:
    """(kind, paper code, session) as printed on the document itself."""
    try:
        with fitz.open(stream=body, filetype="pdf") as d:
            page1 = " ".join(d[0].get_text().split())
            head = " ".join(" ".join(d[i].get_text() for i in range(min(3, d.page_count))).split())
            pages = d.page_count
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unreadable ({type(exc).__name__})"}
    kind = "MS" if MS_RE.search(page1) else "QP"
    m = REF_RE.search(head) or PAPER_RE.search(head)
    paper = m.group(1).upper() if m else None
    s = SESSION_RE.search(page1)
    return {"kind": kind, "paper": paper, "pages": pages,
            "session": s.group(0) if s else None}


# A November 2020 question paper prints either November or -- because Pearson
# reprinted the cancelled summer papers unchanged -- the original May/June date.
# It never prints January, so a January cover positively identifies the wrong
# paper (which is exactly the defect in Mathematics A's oct-nov tier rows).
QP_OK_MONTHS = ("may", "june", "november")


def is_november_2020(info: dict) -> bool:
    """Mark schemes must say November 2020; question papers May/June/November 2020."""
    if not info["session"] or not info["session"].endswith(YEAR):
        return False
    month = info["session"].split()[0].lower()
    if info["kind"] == "MS":
        return month == "november"
    return month in QP_OK_MONTHS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    client = r2_client()
    plan = []

    for subject, (folder, code_of) in SUBJECTS.items():
        sid = requests.get(f"{SUPABASE_URL}/rest/v1/subjects?select=id&name=eq."
                           f"{subject.replace(' ', '%20')}", headers=H, timeout=60).json()[0]["id"]
        rows = requests.get(f"{SUPABASE_URL}/rest/v1/papers?select=id,season,paper_number,"
                            f"pdf_url,markscheme_pdf_url&subject_id=eq.{sid}&year=eq.{YEAR}",
                            headers=H, timeout=60).json()
        bad = [r for r in rows if r["season"] == "may-jun"]
        good = [r for r in rows if r["season"] == "oct-nov"]
        print(f"\n########## {subject} {YEAR}")

        # index the correct November set, by the paper code printed on the cover
        library: dict[tuple[str, str], tuple[str, bytes]] = {}
        for r in bad:
            for col, kind in (("pdf_url", "QP"), ("markscheme_pdf_url", "MS")):
                k = key_of(r.get(col))
                if not k:
                    continue
                try:
                    body = client.get_object(Bucket=R2_BUCKET, Key=k)["Body"].read()
                except Exception as exc:  # noqa: BLE001
                    print(f"   cannot read {k}: {exc}")
                    continue
                info = identify(body)
                if info.get("error") or info["kind"] != kind or not info["paper"]:
                    continue
                if not is_november_2020(info):
                    print(f"   skip {k.split('/')[-1]} -- session {info['session']}")
                    continue
                library.setdefault((info["paper"], kind), (k, body))
        print(f"   November {YEAR} library: "
              f"{sorted(f'{p}/{k}' for p, k in library)}")

        for r in sorted(good, key=lambda r: str(r["paper_number"])):
            pn = str(r["paper_number"])
            want = code_of.get(pn)
            if not want:
                print(f"   oct-nov paper {pn}: no code mapping; left alone")
                continue
            for col, kind in (("pdf_url", "QP"), ("markscheme_pdf_url", "MS")):
                entry = library.get((want, kind))
                if not entry:
                    continue
                _src_key, body = entry
                cur_key = key_of(r.get(col))
                # is the current file already the right document?
                if cur_key:
                    try:
                        cur = client.get_object(Bucket=R2_BUCKET, Key=cur_key)["Body"].read()
                        cur_info = identify(cur)
                        if (not cur_info.get("error") and cur_info["paper"] == want
                                and is_november_2020(cur_info)):
                            continue  # already correct
                        reason = (f"is {cur_info.get('paper')} {cur_info.get('session')}"
                                  if not cur_info.get("error") else cur_info["error"])
                    except Exception:  # noqa: BLE001
                        reason = "unreadable"
                else:
                    reason = "empty"
                dst_key = (cur_key or
                           f"igcse/{folder.lower()}/{YEAR}/oct-nov/"
                           f"{folder}_{YEAR}_Oct-Nov_Paper_{pn}_{kind}.pdf")
                print(f"   oct-nov paper {pn:4} {kind}: {reason}  ->  {want} Nov {YEAR}")
                plan.append({"subject": subject, "paper": pn, "kind": kind,
                             "key": dst_key, "reason": reason})
                if args.commit:
                    client.put_object(Bucket=R2_BUCKET, Key=dst_key, Body=body,
                                      ContentType="application/pdf")
                    resp = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/papers?id=eq.{r['id']}", headers={**H,
                        "Content-Type": "application/json"},
                        json={col: f"{R2_PUBLIC}/{dst_key}"}, timeout=60)
                    if resp.status_code not in (200, 204):
                        print(f"      DB patch failed {resp.status_code}: {resp.text[:120]}")

        # remove the phantom session
        keys = [k for r in bad for k in
                (key_of(r.get("pdf_url")), key_of(r.get("markscheme_pdf_url"))) if k]
        print(f"   -> delete {len(bad)} may-jun row(s), {len(keys)} R2 object(s)")
        if args.commit:
            dest = BACKUP / folder
            dest.mkdir(parents=True, exist_ok=True)
            for k in keys:
                try:
                    (dest / k.split("/")[-1]).write_bytes(
                        client.get_object(Bucket=R2_BUCKET, Key=k)["Body"].read())
                except Exception as exc:  # noqa: BLE001
                    print(f"      backup failed {k}: {exc}")
            for k in keys:
                client.delete_object(Bucket=R2_BUCKET, Key=k)
            for r in bad:
                requests.delete(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{r['id']}",
                                headers=H, timeout=60)
            local = ARCHIVE / folder / YEAR / "May-Jun"
            if local.exists():
                tgt = dest / "archive"
                if tgt.exists():
                    shutil.rmtree(tgt)
                shutil.move(str(local), str(tgt))

    BACKUP.mkdir(parents=True, exist_ok=True)
    (BACKUP / "chem_mathsa_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: {len(plan)} file(s) corrected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
