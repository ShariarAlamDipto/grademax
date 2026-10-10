#!/usr/bin/env python3
"""Watch for the public release of the 2026 Edexcel IAL / IGCSE exam series.

Pearson publishes every series twice. First to exam centres only, under
`/content/dam/secure/...`, which 302s anonymous requests to
`edexcelonline.pearson.com/Account/Login.aspx`. Some months later the same asset
is re-pointed at a public `/content/dam/...` path and becomes freely
downloadable. Every series up to and including June 2025 has completed that
transition; as of 2026-08-20 all three 2026 series are still centre-only:

    IAL   January-2026    414 / 417 secure
    IAL   June-2026       412 / 415 secure
    IGCSE June-2026       419 / 419 secure

This script re-checks that split and reports which 2026 question papers and mark
schemes have become publicly downloadable. It is read-only — it never writes to
R2 or the database. Once it reports a non-zero "public" count, feed the manifest
to the existing ingest path (scripts/fill_ial_gaps_from_algolia.py), which
already handles verify + clean/stamp + upload + DB patch.

Two independent checks must both pass before an asset counts as released:
  1. the Algolia URL is not under /dam/secure/, and
  2. an anonymous GET actually returns application/pdf rather than the
     Edexcel Online login redirect.

Check 2 matters because the index and the CDN are not updated atomically.

Usage:
    python -X utf8 scripts/watch_2026_release.py                    # summary
    python -X utf8 scripts/watch_2026_release.py --verbose          # per-asset
    python -X utf8 scripts/watch_2026_release.py --json out.json    # manifest
"""
import argparse
import io
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import httpx

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

APP_ID = "L639T95U5A"
API_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"
INDEX = "qualifications-uk_LIVE_master-content"
ALGOLIA = (
    f"https://{APP_ID.lower()}-dsn.algolia.net/1/indexes/{INDEX}/query"
    f"?x-algolia-application-id={APP_ID}&x-algolia-api-key={API_KEY}"
)
PEARSON_HOST = "https://qualifications.pearson.com"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
}

# (qualification family, exam series) pairs that make up the 2026 archive gap.
TARGETS = [
    ("International-Advanced-Level", "January-2026"),
    ("International-Advanced-Level", "June-2026"),
    ("International-GCSE", "June-2026"),
]

SECURE_MARKER = "/dam/secure/"
LOGIN_MARKER = "edexcelonline"


def algolia_hits(family: str, series: str) -> list[dict]:
    """Every indexed asset for one (family, series), following pagination."""
    filters = (
        f'category:"Pearson-UK:Qualification-Family/{family}"'
        f' AND category:"Pearson-UK:Exam-Series/{series}"'
        ' AND type:"dam:Asset"'
    )
    hits: list[dict] = []
    page = 0
    while page < 30:
        payload = {
            "params": f"query=&filters={quote(filters, safe='')}&hitsPerPage=1000&page={page}"
        }
        r = httpx.post(ALGOLIA, json=payload, timeout=45)
        if r.status_code != 200:
            print(f"  ! Algolia {r.status_code} for {family}/{series}", file=sys.stderr)
            break
        data = r.json()
        hits.extend(data.get("hits", []))
        if page + 1 >= data.get("nbPages", 1):
            break
        page += 1
    return hits


def asset_kind(hit: dict) -> str | None:
    """QP / MS, or None for the ancillary assets we don't host."""
    title = (hit.get("title") or "").lower()
    url = (hit.get("url") or "").lower()
    cats = " ".join(str(c).lower() for c in (hit.get("category") or []))
    if "document-type/mark" in cats or "mark scheme" in title or "-rms-" in url:
        return "MS"
    if "document-type/question" in cats or "question paper" in title or "-que-" in url:
        return "QP"
    return None


def subject_of(hit: dict) -> str:
    for c in hit.get("category") or []:
        m = re.search(r"Qualification-Subject/([\w-]+)", str(c))
        if m:
            return m.group(1)
    return "?"


def probe(url: str) -> tuple[bool, str]:
    """True only when an anonymous GET yields a real PDF (not the login wall)."""
    try:
        r = httpx.get(
            PEARSON_HOST + url, headers=UA, timeout=45, follow_redirects=True
        )
    except Exception as e:  # network flake — report, never crash the sweep
        return False, f"error: {type(e).__name__}"
    final = str(r.url).lower()
    if LOGIN_MARKER in final:
        return False, "login-gated"
    ctype = r.headers.get("content-type", "")
    if r.status_code == 200 and "pdf" in ctype.lower():
        return True, f"public ({len(r.content):,}b)"
    return False, f"http {r.status_code} {ctype[:24]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="list every released asset")
    ap.add_argument("--json", metavar="PATH", help="write a manifest of released assets")
    ap.add_argument(
        "--probe-limit",
        type=int,
        default=40,
        help="max non-secure assets to GET-verify per series (default 40)",
    )
    args = ap.parse_args()

    released: list[dict] = []
    print(f"{'series':<46} {'QP+MS':>6} {'secure':>7} {'public':>7}")
    print("-" * 70)

    for family, series in TARGETS:
        hits = algolia_hits(family, series)
        papers = [h for h in hits if asset_kind(h)]
        secure = [h for h in papers if SECURE_MARKER in (h.get("url") or "")]
        candidates = [h for h in papers if SECURE_MARKER not in (h.get("url") or "")]

        # Index and CDN aren't updated atomically — confirm with a real request.
        confirmed: list[dict] = []
        to_probe = candidates[: args.probe_limit]
        if to_probe:
            with ThreadPoolExecutor(max_workers=6) as ex:
                results = list(ex.map(lambda h: probe(h.get("url") or ""), to_probe))
            for hit, (ok, why) in zip(to_probe, results):
                if ok:
                    confirmed.append(hit)
                    released.append(
                        {
                            "family": family,
                            "series": series,
                            "subject": subject_of(hit),
                            "kind": asset_kind(hit),
                            "title": hit.get("title"),
                            "url": PEARSON_HOST + (hit.get("url") or ""),
                        }
                    )
                elif args.verbose:
                    print(f"    skip {why:<22} {(hit.get('title') or '')[:52]}")

        label = f"{family.replace('International-', 'Int ')} {series}"
        print(f"{label:<46} {len(papers):>6} {len(secure):>7} {len(confirmed):>7}")

    print("-" * 70)
    if not released:
        print(
            "\nNo 2026 paper has been de-gated yet — all are still centre-only.\n"
            "Nothing to ingest. Re-run this periodically; historically a series\n"
            "goes public roughly 9-12 months after it is sat."
        )
        return 0

    print(f"\n{len(released)} asset(s) now public and ready to ingest:")
    by_subject: dict[str, list[dict]] = defaultdict(list)
    for a in released:
        by_subject[f"{a['series']} {a['subject']}"].append(a)
    for key in sorted(by_subject):
        kinds = ", ".join(sorted(x["kind"] for x in by_subject[key]))
        print(f"  {key:<44} {kinds}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(released, fh, indent=2)
        print(f"\nmanifest -> {args.json}")
    print(
        "\nNext: run scripts/fill_ial_gaps_from_algolia.py (dry-run first, then "
        "--commit)\nto verify, clean, stamp, upload to R2 and patch the DB."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
