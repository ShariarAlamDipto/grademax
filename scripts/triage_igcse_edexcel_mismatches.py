#!/usr/bin/env python3
"""Decide, for every Edexcel IGCSE label mismatch, which repair it needs.

`audit_igcse_edexcel_labels.py` says *that* a file contradicts its slot. It does
not say what to do about it, and the three possible repairs are very different:

  DUPLICATE  the document is already filed correctly somewhere else, so this slot
             is a redundant listing of it -> drop the row/file.
  RELABEL    the document is genuine and unique, but belongs in a different slot
             that is currently empty -> move it there.
  REPLACE    the slot names a paper that really exists and this is not it -> the
             correct document has to be sourced.

Telling them apart needs content identity, and md5 is not enough: every archived
PDF carries a GradeMax stamp applied at ingest time, so two copies of the same
Pearson document taken on different days differ byte-for-byte. Mark schemes also
carry no barcode. So identity here is a *text* fingerprint with the stamp and any
PMT residue normalised out.

Read-only. Writes a plan to data/analysis/igcse_mismatch_plan.json.

Usage:
    python -X utf8 scripts/triage_igcse_edexcel_mismatches.py
    python -X utf8 scripts/triage_igcse_edexcel_mismatches.py --subject Accounting
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from audit_igcse_edexcel_labels import ARCHIVE_ROOT, FILENAME_RE  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON = REPO_ROOT / "data" / "analysis" / "igcse_edexcel_label_audit.json"
OUT_PLAN = REPO_ROOT / "data" / "analysis" / "igcse_mismatch_plan.json"

# Everything the stamping/cleaning pipeline can add or remove, plus the page
# furniture that legitimately differs between two prints of the same paper.
NOISE_RE = re.compile(
    r"grademax(?:\.me)?|physicsandmathstutor(?:\.com)?|pmt\b|"
    r"https?://\S+|www\.\S+|\bpage\s*\d+\s*of\s*\d+\b",
    re.I)
NONWORD_RE = re.compile(r"[^a-z0-9]+")


def fingerprint(path: Path) -> dict:
    """Stamp-insensitive content identity for one PDF."""
    try:
        with fitz.open(path) as doc:
            pages = [doc[i].get_text() for i in range(doc.page_count)]
            n = doc.page_count
    except Exception as exc:  # noqa: BLE001
        return {"file": str(path.relative_to(REPO_ROOT)), "error": type(exc).__name__}
    body = NOISE_RE.sub(" ", " ".join(pages))
    body = NONWORD_RE.sub("", body.lower())
    # A short prefix hash catches "same paper, different scan/print" where later
    # pages were re-flowed; the full hash is the strict test.
    return {
        "file": str(path.relative_to(REPO_ROOT)),
        "full": hashlib.md5(body.encode()).hexdigest(),
        "head": hashlib.md5(body[:4000].encode()).hexdigest(),
        "chars": len(body),
        "pages": n,
    }


def slot_of(rel: str) -> tuple[str, str, str, str, str] | None:
    """(subject, year, season, paper, kind) from an archive path."""
    p = Path(rel)
    m = FILENAME_RE.match(p.name)
    if not m:
        return None
    subject = p.relative_to(Path("data/Ultimate Final IGCSE")).parts[0]
    return (subject, m.group("year"), p.parent.name,
            m.group("paper").upper(), m.group("kind"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    audit = json.loads(AUDIT_JSON.read_text("utf-8"))
    if args.subject:
        audit = [r for r in audit if r["subject"].lower() == args.subject.lower()]
    bad = [r for r in audit if r["status"] == "MISMATCH"]
    if not bad:
        print("no mismatches in audit")
        return 0

    # Fingerprint only the subjects that actually have a defect -- a twin can only
    # be inside the same subject.
    subjects = {r["subject"] for r in bad}
    scope = [r for r in audit if r["subject"] in subjects]
    paths = [REPO_ROOT / r["file"] for r in scope]
    print(f"fingerprinting {len(paths)} PDFs in {len(subjects)} subject(s) ...")

    fps: dict[str, dict] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for fp in ex.map(fingerprint, paths, chunksize=8):
            fps[fp["file"]] = fp

    by_full = defaultdict(list)
    by_head = defaultdict(list)
    for f, fp in fps.items():
        if fp.get("error"):
            continue
        by_full[fp["full"]].append(f)
        by_head[fp["head"]].append(f)

    audit_by_file = {r["file"]: r for r in audit}
    existing_slots = {slot_of(r["file"]) for r in audit if slot_of(r["file"])}

    plan = []
    for r in bad:
        fp = fps.get(r["file"], {})
        mine = slot_of(r["file"])
        twins = [t for t in by_full.get(fp.get("full", ""), []) if t != r["file"]]
        near = [t for t in by_head.get(fp.get("head", ""), [])
                if t != r["file"] and t not in twins]

        # Which of those twins is filed under a slot the audit calls clean?
        good_twins = [t for t in twins + near
                      if audit_by_file.get(t, {}).get("status") in ("OK", "CONVENTION")]

        entry = {
            "file": r["file"], "subject": r["subject"], "slot": r["slot"],
            "issues": r["issues"], "evidence": r["evidence"],
            "barcode": r.get("barcode"), "pages": fp.get("pages"),
            "found_paper": r.get("found"),
            "twins_exact": twins, "twins_head": near,
            "clean_twins": good_twins,
        }

        # Where does this document actually belong?
        target = None
        sess = next((i for i in r["issues"] if i.startswith("session ")), None)
        if sess and mine:
            m = re.match(r"session \S+->(\d{4})/(\S+)", sess)
            if m:
                target = (mine[0], m.group(1), m.group(2), mine[3], mine[4])
        pap = next((i for i in r["issues"] if i.startswith("paper ")), None)
        if pap and mine and not target:
            m = re.match(r"paper \S+->(\S+)", pap)
            if m:
                target = (mine[0], mine[1], mine[2], m.group(1).upper(), mine[4])
        entry["target_slot"] = ("/".join(target[1:]) if target else None)
        entry["target_slot_occupied"] = bool(target and target in existing_slots)

        if good_twins:
            entry["action"] = "DUPLICATE"
            entry["why"] = f"same content already filed as {good_twins[0].split('Paper_')[-1]}"
        elif target and not entry["target_slot_occupied"]:
            entry["action"] = "RELABEL"
            entry["why"] = f"unique document; its real slot {entry['target_slot']} is empty"
        else:
            entry["action"] = "REPLACE"
            entry["why"] = ("real slot already occupied" if entry["target_slot_occupied"]
                            else "unique document, slot needs correct paper sourced")
        plan.append(entry)

    OUT_PLAN.parent.mkdir(parents=True, exist_ok=True)
    OUT_PLAN.write_text(json.dumps(plan, indent=1), encoding="utf-8")

    counts = defaultdict(int)
    for e in plan:
        counts[e["action"]] += 1
    for subj in sorted({e["subject"] for e in plan}):
        print(f"\n{'=' * 76}\n{subj}")
        for e in [x for x in plan if x["subject"] == subj]:
            print(f"  [{e['action']:<9}] {e['slot']:<34} {'; '.join(e['issues'])}")
            print(f"              {e['why']}")
            for t in e["clean_twins"][:2]:
                print(f"              twin: {Path(t).name}")
    print(f"\n{'=' * 76}")
    print("  ".join(f"{k}={v}" for k, v in sorted(counts.items())), f" total={len(plan)}")
    print(f"plan -> {OUT_PLAN.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
