"""
Replace the live papers/mark schemes that the yearwise linkage audit proved
wrong (another unit's paper, the 01R time-zone or 01A adapted variant), using
the verified correct document the same audit linked for that sitting.

Source of truth: `data/yearwise_all/linkage/<book>.json`. A DB copy the audit
REJECTED for a sitting that is now LINKED through another copy (Pearson's own,
the archive, or Paperlords) is a wrong live file with a known-good replacement.

Per file, with --apply:
  1. back up the live R2 object to data/backups/yearwise_live_fix_<date>/
  2. clean + stamp the replacement exactly as ingest does (clean_and_stamp)
  3. re-identify the stamped bytes -- the cover/title must still name the unit
  4. overwrite the SAME R2 key (the DB row's URL is unchanged)
  5. re-download from the public URL (cache-busted) and compare bytes

Refuses any key that more than one DB row points at.

    python -X utf8 scripts/fix_live_yearwise_wrong_files.py            # dry run
    python -X utf8 scripts/fix_live_yearwise_wrong_files.py --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import tempfile
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

_argv, sys.argv = sys.argv, [sys.argv[0]]
import ingest_2026_papers as ing  # noqa: E402
from ingest_cambridge_papers import clean_and_stamp  # noqa: E402
sys.argv = _argv

from lib.yearwise_all_catalogue import ROOT, UNITS, WORK  # noqa: E402
from lib.yearwise_linkage import _judge_ms, _judge_qp, Sitting, _read, Doc  # noqa: E402

REJECTED = re.compile(r"(QP|MS) (db:\S+) \((\d{4}) ([\w-]+)\): (.*)")
# These rows hold a consistent legacy GCE pair (C2 QP + C2 scheme) under a P2/P4
# label: a labelling question, not a wrong file, so they are left alone.
SKIP = {("WMA12", "2018 May-Jun"), ("WMA14", "2018 May-Jun")}


def plan() -> list[dict]:
    cands = {}
    for f in (WORK / "candidates").glob("*.json"):
        cands.update(json.loads(f.read_text(encoding="utf-8")))
    out = []
    for f in sorted((WORK / "linkage").glob("*.json")):
        for u in json.loads(f.read_text(encoding="utf-8")):
            for s in u["sittings"]:
                if (u["unit"], s["sitting"]) in SKIP:
                    continue
                for r in s["rejected"]:
                    m = REJECTED.match(r)
                    if not m:
                        continue
                    kind, source, year, season, why = m.groups()
                    url = next(c["url"] for c in cands[u["unit"]]
                               if c["kind"] == kind and c["source"] == source
                               and c["year"] == int(year) and c["season"] == season)
                    good = s["qp"] if kind == "QP" else s["ms"]
                    out.append({"unit": u["unit"], "sitting": s["sitting"], "kind": kind,
                                "verdict": s["verdict"], "why": why, "url": url,
                                "replacement": good["path"] if good and good["source"] != source.split(":")[0]
                                and not good["source"].startswith("db") else None,
                                "replacement_source": good and good["source"]})
    # One live URL can be rejected under two sittings only by mistake; dedupe.
    return list({(p["url"], p["kind"]): p for p in out}.values())


def rows_pointing_at(url: str) -> int:
    n = 0
    for col in ("pdf_url", "markscheme_pdf_url"):
        rows = httpx.get(f"{ing.SUPABASE_URL}/rest/v1/papers", headers=ing.H, timeout=60,
                         params={"select": "id", col: f"eq.{url}"}).json()
        n += len(rows)
    return n


def still_identifies(unit_key: str, sitting: str, kind: str, data: bytes) -> str | None:
    """None if the stamped bytes still pass the audit's identity check."""
    unit = next(u for u in UNITS if u.key == unit_key)
    year, season = sitting.split(" ", 1)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
    path = Path(tmp.name)
    try:
        info = _read(path, kind)
    finally:
        path.unlink()
    head = info.pop("head")
    doc = Doc(path="-", source="-", **info)
    s = Sitting(int(year), season)
    return _judge_qp(unit, s, doc, head) if kind == "QP" else _judge_ms(unit, s, doc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    items = plan()
    backup = ROOT / "data" / "backups" / f"yearwise_live_fix_{dt.date.today():%Y%m%d}"
    r2 = ing.get_r2() if args.apply else None
    log = []
    print(f"{len(items)} wrong live files\n")
    for p in items:
        label = f"{p['unit']} {p['sitting']} {p['kind']}"
        key = p["url"][len(ing.R2_PUBLIC_URL) + 1:]
        if not p["url"].startswith(ing.R2_PUBLIC_URL) or p["verdict"] != "LINKED" or not p["replacement"]:
            print(f"  SKIP {label}: no verified replacement (verdict {p['verdict']}) -- {p['why']}")
            continue
        shared = rows_pointing_at(p["url"])
        if shared != 1:
            print(f"  SKIP {label}: {shared} DB rows point at {key}")
            continue
        body = (ROOT / p["replacement"]).read_bytes()
        cleaned, redactions, _ = clean_and_stamp(body)
        why = still_identifies(p["unit"], p["sitting"], p["kind"], cleaned)
        if why:
            print(f"  STOP {label}: stamped replacement no longer identifies ({why})")
            continue
        print(f"  {'fix ' if args.apply else 'would'} {label}: was \"{p['why']}\" -> "
              f"{p['replacement_source']} copy ({len(cleaned) // 1024}KB, {redactions} redactions)\n"
              f"        key {key}")
        if not args.apply:
            continue
        old = httpx.get(p["url"], timeout=120).content
        dest = backup / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(old)
        r2.put_object(Bucket=ing.R2_BUCKET, Key=key, Body=cleaned, ContentType="application/pdf")
        time.sleep(1)
        live = httpx.get(f"{p['url']}?v={int(time.time())}", timeout=120).content
        ok = hashlib.sha256(live).digest() == hashlib.sha256(cleaned).digest()
        print(f"        {'VERIFIED' if ok else 'MISMATCH'} from the public URL")
        log.append({**p, "key": key, "backup": str(dest.relative_to(ROOT)), "verified": ok})
    if args.apply:
        out = backup / "fix_log.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(log, indent=1), encoding="utf-8")
        print(f"\nlog: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
