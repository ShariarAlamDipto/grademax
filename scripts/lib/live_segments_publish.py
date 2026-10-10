"""
Publish rebuilt, proven question + mark-scheme segments to the live `pages`
layer (and its `questions` mirror) that the test builder and worksheet
generator serve. Subject-neutral; each subject has a thin entry script.

THE RULE: A MARK SCHEME IS SHOWN ONLY WHEN IT IS PROVEN
-------------------------------------------------------
For every live question of the subject, after this runs:

  ms_page_url = the rebuilt scheme   when the rebuild PROVED the pair
              = the current scheme   when the row was not rebuilt but the
                                     live content audit PROVED its current pair
              = NULL                 otherwise

NULL renders "Mark scheme not available -- check the full paper's mark
scheme" (src/lib/questionPdfAssembly.ts). A wrong scheme is never preferred
over that.

WHAT IS WRITTEN, AND HOW TO UNDO IT
-----------------------------------
* New objects only: <r2_folder>/pages-v2/<paper>/q<n>.pdf and q<n>_ms.pdf.
  Nothing already in R2 is overwritten, so a rollback is restoring URLs.
* Existing `pages` rows are UPDATED IN PLACE (ids, topics, difficulty kept)
  because saved tests and worksheets reference them by id.
* A live row whose number the rebuilt paper does not have (an old bundle,
  e.g. "q9" holding Q4-Q8 of an 8-question paper) loses both URLs, which hides
  it from both tools; the row stays so saved items do not dangle.
* A rebuilt question with no live row is INSERTED with no topics: it is
  correct but unclassified, so topic-filtered tools do not pick it until it
  is classified (reported).
* `questions` (same ids; saved-worksheet re-downloads read it) is mirrored.
* Before any write the subject's `pages` and `questions` rows are backed up to
  data/backups/live_ms_linkage_<date>/<CODE>_{pages,questions}.json.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import time
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from lib.live_paper_sources import ROOT, fetch_rows, r2_reader, subject_id, supabase_client

PROVEN_LIVE = {"PROVEN"}
# `pages` is UNIQUE (paper_id, page_number) and the site only orders by it.
# Rebuilt rows take 1000 + question number: unique per paper, clear of every
# old value, and in question order. (The first Physics publish stopped on this
# constraint at the inserts, after the updates had applied.)
PAGE_BASE = 1000
QP_BAD = {"QP_BUNDLED", "QP_WRONG"}


@dataclass
class Plan:
    updates: list[dict] = field(default_factory=list)   # {id, qp_page_url?, ms_page_url}
    inserts: list[dict] = field(default_factory=list)
    hides: list[str] = field(default_factory=list)
    uploads: list[tuple[Path, str]] = field(default_factory=list)  # (local file, key)
    counts: dict[str, int] = field(default_factory=dict)

    def bump(self, name: str) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1


def _qnum(text: str) -> int | None:
    match = re.match(r"\d+", str(text))
    return int(match.group()) if match else None


def build_plan(code: str, r2_folder: str, verdicts: dict, live_audit: dict,
               publishable: set[str], public_prefix: str) -> tuple[Plan, list[dict]]:
    sb = supabase_client()
    sid = subject_id(sb, code)
    papers = fetch_rows(lambda o: sb.table("papers").select("id").eq("subject_id", sid)
                        .range(o, o + 999))
    ids = [p["id"] for p in papers]
    rows: list[dict] = []
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        rows += fetch_rows(lambda o, part=part: sb.table("pages").select("*")
                           .in_("paper_id", part).range(o, o + 999))

    live_verdict = {r["page_id"]: r["verdict"] for r in live_audit["rows"]}
    rebuilt: dict[str, dict[int, dict]] = {}
    for row in verdicts["rows"]:
        rebuilt.setdefault(row["paper_id"], {})[row["question"]] = row

    plan = Plan()
    by_paper: dict[str, list[dict]] = {}
    for row in rows:
        by_paper.setdefault(row["paper_id"], []).append(row)

    def key_for(row: dict, kind: str) -> str:
        # The content hash is part of the name: a re-cut file gets a NEW URL,
        # so neither the public CDN cache nor a same-size skip can keep
        # serving the old cut.
        suffix = "_ms" if kind == "ms" else ""
        local = ROOT / (row["ms"] if kind == "ms" else row["qp"])
        digest = hashlib.md5(local.read_bytes()).hexdigest()[:10]
        return (f"{r2_folder}/pages-v2/{row['live_key']}/"
                f"q{row['question']}{suffix}-{digest}.pdf")

    for paper_id in set(by_paper) | set(rebuilt):
        live_rows = [r for r in by_paper.get(paper_id, []) if r["qp_page_url"]]
        new = rebuilt.get(paper_id)
        if not new:
            # Not rebuilt: keep the question, keep the scheme only if proven.
            for r in live_rows:
                proven = live_verdict.get(r["id"]) in PROVEN_LIVE
                if live_verdict.get(r["id"]) in QP_BAD:
                    # An old bundle (q2.pdf holding Q1-Q3) is a wrong question
                    # file, not just a wrong scheme: hide it until rebuilt.
                    plan.hides.append(r["id"])
                    plan.bump("not rebuilt: bundled/wrong question file hidden")
                    continue
                if r["ms_page_url"] and not proven:
                    plan.updates.append({"id": r["id"], "ms_page_url": None})
                    plan.bump("not rebuilt: unproven scheme removed")
                else:
                    plan.bump("not rebuilt: unchanged")
            continue

        seen: set[int] = set()
        for r in live_rows:
            number = _qnum(r["question_number"])
            item = new.get(number) if number is not None else None
            if item is None:
                plan.hides.append(r["id"])
                plan.bump("live row with no such question: hidden")
                continue
            seen.add(number)
            change = _change_for(item, publishable, key_for, public_prefix, plan)
            plan.updates.append({"id": r["id"], "page_number": PAGE_BASE + number,
                                 "page_count": item.get("page_count", 1), **change})
        for number, item in sorted(new.items()):
            if number in seen:
                continue
            change = _change_for(item, publishable, key_for, public_prefix, plan)
            if "qp_page_url" not in change:
                plan.bump("new question with unusable file: skipped")
                continue
            plan.inserts.append({
                "paper_id": paper_id, "question_number": str(number), "topics": [],
                "is_question": True, "difficulty": None,
                "page_number": PAGE_BASE + number, "page_count": item.get("page_count", 1),
                **change,
            })
            plan.bump("new question inserted (unclassified)")
    return plan, rows


def _change_for(item: dict, publishable: set[str], key_for, public_prefix: str,
                plan: Plan) -> dict:
    change: dict = {}
    if item["verdict"] not in QP_BAD:
        qp_key = key_for(item, "qp")
        plan.uploads.append((ROOT / item["qp"], qp_key))
        change["qp_page_url"] = public_prefix + qp_key
    if item["verdict"] in publishable and item["ms"]:
        ms_key = key_for(item, "ms")
        plan.uploads.append((ROOT / item["ms"], ms_key))
        change["ms_page_url"] = public_prefix + ms_key
        plan.bump("scheme proven and linked")
    else:
        change["ms_page_url"] = None
        plan.bump(f"scheme withheld ({item['verdict']})")
    return change


def backup(code: str, pages_rows: list[dict]) -> Path:
    sb = supabase_client()
    # Timestamped per run: a re-run must never overwrite the pre-change copy
    # (the first Physics re-run did, 2026-10-07; the original was recovered
    # from the audit + census snapshots).
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "data" / "backups" / f"live_ms_linkage_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    ids = [r["id"] for r in pages_rows]
    mirror: list[dict] = []
    for i in range(0, len(ids), 100):
        mirror += sb.table("questions").select("*").in_("id", ids[i:i + 100]).execute().data or []
    (out / f"{code}_pages.json").write_text(json.dumps(pages_rows, indent=1), encoding="utf-8")
    (out / f"{code}_questions.json").write_text(json.dumps(mirror, indent=1), encoding="utf-8")
    return out


UPLOAD_ATTEMPTS = 6


def _put_with_retry(r2, bucket: str, key: str, body: bytes) -> None:
    """R2 drops connections now and then (the first Maths B publish died on
    one, 2026-10-07, before any DB write); retry with backoff."""
    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        try:
            r2.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/pdf")
            return
        except Exception:  # noqa: BLE001 -- network errors of several botocore kinds
            if attempt == UPLOAD_ATTEMPTS:
                raise
            time.sleep(2 ** attempt)


def execute(code: str, plan: Plan, pages_rows: list[dict]) -> None:
    import ingest_2026_papers as ing  # noqa: PLC0415 -- env loaded by r2_reader

    r2_reader()
    r2 = ing.get_r2()
    folder = backup(code, pages_rows)
    print(f"backup  : {folder}")

    existing: dict[str, int] = {}
    prefixes = {key.rsplit("/", 2)[0] + "/" for _, key in plan.uploads}
    for prefix in prefixes:
        for page in r2.get_paginator("list_objects_v2").paginate(Bucket=ing.R2_BUCKET,
                                                                  Prefix=prefix):
            for obj in page.get("Contents", []):
                existing[obj["Key"]] = obj["Size"]
    done: set[str] = set()
    for local, key in plan.uploads:
        if key in done:
            continue
        if key in existing:  # content-addressed: same name, same bytes
            done.add(key)
            continue
        _put_with_retry(r2, ing.R2_BUCKET, key, local.read_bytes())
        done.add(key)
    print(f"uploaded: {len(done)} objects")

    sb = supabase_client()
    mirror_ids = {r["id"] for r in json.loads(
        (folder / f"{code}_questions.json").read_text(encoding="utf-8"))}
    for change in plan.updates:
        fields = {k: v for k, v in change.items() if k != "id"}
        sb.table("pages").update(fields).eq("id", change["id"]).execute()
        if change["id"] in mirror_ids:
            mirrored = {"ms_pdf_url": fields["ms_page_url"]} if "ms_page_url" in fields else {}
            if "qp_page_url" in fields:
                mirrored["page_pdf_url"] = fields["qp_page_url"]
            sb.table("questions").update(mirrored).eq("id", change["id"]).execute()
    for page_id in plan.hides:
        sb.table("pages").update({"qp_page_url": None, "ms_page_url": None}).eq("id", page_id).execute()
        if page_id in mirror_ids:
            sb.table("questions").update({"page_pdf_url": None, "ms_pdf_url": None}) \
                .eq("id", page_id).execute()
    for start in range(0, len(plan.inserts), 100):
        created = sb.table("pages").insert(plan.inserts[start:start + 100]).execute().data or []
        sb.table("questions").upsert([{
            "id": c["id"], "paper_id": c["paper_id"], "question_number": c["question_number"],
            "difficulty": c.get("difficulty"), "page_pdf_url": c["qp_page_url"],
            "ms_pdf_url": c["ms_page_url"], "has_diagram": False,
        } for c in created]).execute()
    print(f"updated : {len(plan.updates)}  hidden: {len(plan.hides)}  inserted: {len(plan.inserts)}")


def run(code: str, r2_folder: str, stage_dir: Path, publishable: set[str], *,
        do_execute: bool) -> int:
    verdicts = json.loads((stage_dir / "verdicts.json").read_text(encoding="utf-8"))
    live_audit = json.loads((ROOT / "data" / "analysis" / "live_ms_linkage" / f"{code}.json")
                            .read_text(encoding="utf-8"))
    _, prefix = r2_reader()
    plan, rows = build_plan(code, r2_folder, verdicts, live_audit, publishable, prefix)
    print(f"=== {code} -> live pages  [{'EXECUTE' if do_execute else 'DRY RUN'}] ===")
    for name, n in sorted(plan.counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {name}")
    print(f"  uploads planned: {len({k for _, k in plan.uploads})}")
    if do_execute:
        execute(code, plan, rows)
    else:
        print("\nDry run only. Re-run with --execute to write.")
    return 0
