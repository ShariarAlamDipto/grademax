#!/usr/bin/env python3
"""Re-upload the clean IAL Maths question papers to R2, replacing the PMT Model
Answers that are still being served in production.

Background
----------
On 2026-07-21 `scripts/fix_ial_maths_model_answer_qps.py` replaced 165 mislabelled
`*_QP.pdf` files in `data/Ultimate Final IAL/{Mathematics,Further_Mathematics}`
with the genuine question papers, and moved the 164 originals to
`data/quarantine/ial_maths_model_answers/`.

That fix never reached R2.  A 2026-09-21 audit compared every R2 ETag against the
local archive MD5 and found 164 live `ial/**/*_QP.pdf` objects that are still
byte-identical to the quarantined Model Answers -- i.e. grademax.me has been
serving handwritten worked solutions under the "QP" option for those sessions.

What this script does
---------------------
For every R2 object under `ial/` whose bytes equal a quarantined Model Answer:
  1. locate the clean replacement in the archive (matched by file name),
  2. re-verify the replacement really is a question paper before uploading,
  3. upload it over the stale key.

It refuses to upload anything that does not verify, and it never deletes.

Dry-run by default; pass --commit to write.

Usage:
    python -X utf8 scripts/resync_r2_model_answer_qps.py            # dry-run
    python -X utf8 scripts/resync_r2_model_answer_qps.py --commit
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import boto3
import fitz  # PyMuPDF
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "ial_maths_model_answers"
ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IAL"
PREFIX = "ial/"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def looks_like_question_paper(path: Path) -> tuple[bool, str]:
    """Reject anything carrying the Model-Answer signature.

    Mirrors the validated 2026-09-21 detector: a handwritten Model Answer is
    either a full-page raster scan or coloured/pencil ink, and a genuine paper is
    neither.  Validated at 164/164 recall and 0/164 false alarms on the two
    known truth sets.
    """
    doc = fitz.open(path)
    n = doc.page_count
    idx = list(range(n))[2:10] or list(range(n))[:8]
    big = 0
    for i in idx:
        pg = doc[i]
        area = max(pg.rect.width * pg.rect.height, 1)
        for im in pg.get_images(full=True):
            try:
                r = pg.get_image_rects(im[0])
            except Exception:
                continue
            if r and (r[0].width * r[0].height) / area > 0.55:
                big += 1
                break
    col_px = grey_px = tot_px = 0
    for i in idx[:3]:
        pm = doc[i].get_pixmap(dpi=40)
        s = pm.samples
        for off in range(0, min(len(s), pm.width * pm.height * pm.n), pm.n * 7):
            r, g, b = s[off], s[off + 1], s[off + 2]
            tot_px += 1
            if max(r, g, b) - min(r, g, b) > 40:
                col_px += 1
            elif 70 < r < 200:
                grey_px += 1
    doc.close()
    big_frac = big / max(len(idx), 1)
    colf = col_px / max(tot_px, 1)
    greyf = grey_px / max(tot_px, 1)
    if big_frac >= 0.8:
        return False, f"full-page raster scan ({big_frac:.2f})"
    if colf >= 0.01:
        return False, f"coloured ink pixels ({colf:.4f})"
    if greyf >= 0.05:
        return False, f"pencil/grey handwriting pixels ({greyf:.4f})"
    return True, f"clean (raster={big_frac:.2f} colour={colf:.4f} grey={greyf:.4f})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually upload")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    load_dotenv(REPO_ROOT / ".env.local")
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    bucket = os.environ["R2_BUCKET_NAME"]

    ma_hashes = {md5(p.read_bytes()): p.name for p in QUARANTINE.rglob("*.pdf")}
    print(f"quarantined Model Answers: {len(ma_hashes)}")

    clean = {p.name: p for p in ARCHIVE.rglob("*_QP.pdf")}

    stale = []
    pager = s3.get_paginator("list_objects_v2")
    for page in pager.paginate(Bucket=bucket, Prefix=PREFIX):
        for o in page.get("Contents", []):
            etag = o["ETag"].strip('"')
            if etag in ma_hashes:
                stale.append((o["Key"], etag))
    print(f"live R2 objects still serving a Model Answer: {len(stale)}\n")

    if args.limit:
        stale = stale[: args.limit]

    ok = skipped = failed = 0
    for key, etag in sorted(stale):
        name = key.rsplit("/", 1)[-1]
        repl = clean.get(name)
        if repl is None:
            print(f"  [SKIP] {key}\n         no clean replacement named {name} in archive")
            skipped += 1
            continue
        if md5(repl.read_bytes()) == etag:
            print(f"  [SKIP] {key}\n         archive copy is still the Model Answer")
            skipped += 1
            continue
        good, why = looks_like_question_paper(repl)
        if not good:
            print(f"  [FAIL] {key}\n         replacement rejected: {why}")
            failed += 1
            continue
        if args.commit:
            s3.upload_file(str(repl), bucket, key,
                           ExtraArgs={"ContentType": "application/pdf"})
            print(f"  [DONE] {key}  <- {repl.relative_to(REPO_ROOT)}")
        else:
            print(f"  [DRY ] {key}  <- {repl.relative_to(REPO_ROOT)}  ({why})")
        ok += 1

    verb = "uploaded" if args.commit else "would upload"
    print(f"\n{verb}={ok} skipped={skipped} rejected={failed}")
    if not args.commit and ok:
        print("Dry run only. Re-run with --commit to publish.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
