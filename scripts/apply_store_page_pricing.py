#!/usr/bin/env python3
"""Price every printed book from its page count (user's rule, 7 Nov 2026).

    sheets = ceil(pages / 2)   (printed double-sided: one sheet = two pages)
    cost   = sheets x 1.4 BDT (printing) + 80 BDT (binding)
    profit = the larger of 40% of cost and 150 BDT (user, 7 Nov 2026)
    price  = cost + profit, rounded UP to the next 10 BDT

`page_count` on a variant is the book's PDF page count, i.e. printed sides.

Applies to every listing on sale except the two chapterwise workbooks the
user excluded: Mathematics B (mathematics-b) and Further Pure Mathematics
(further-pure-mathematics). Hidden listings are not touched.

Dry run by default. --commit backs up every store row to data/backups first,
updates each print variant only if its price is still the one read, and
re-reads every row afterwards.

    python -X utf8 scripts/apply_store_page_pricing.py
    python -X utf8 scripts/apply_store_page_pricing.py --commit
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timezone

import requests

from store_cover_targets import ROOT, SUPABASE_URL, headers

PER_SHEET_BDT = 1.4          # one double-sided sheet
PAGES_PER_SHEET = 2
BINDING_BDT = 80
MARKUP = 0.40                # profit as a share of cost
MIN_PROFIT_BDT = 150
ROUND_TO = 10
EXCLUDED = {"mathematics-b", "further-pure-mathematics"}
BACKUP = ROOT / "data/backups" / f"store_page_pricing_{date.today().isoformat()}"


def sheets_for(pages: int) -> int:
    return math.ceil(pages / PAGES_PER_SHEET)


def cost_for(pages: int) -> float:
    return sheets_for(pages) * PER_SHEET_BDT + BINDING_BDT


def price_for(pages: int) -> int:
    cost = cost_for(pages)
    profit = max(cost * MARKUP, MIN_PROFIT_BDT)
    # round() first so float noise (e.g. 515.0000001) cannot push a price up a step
    return int(math.ceil(round(cost + profit, 6) / ROUND_TO) * ROUND_TO)


def load() -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/store_products", headers=headers(), timeout=60, params={
        "select": "id,slug,title,is_active,sort_order,store_variants(id,kind,price_bdt,page_count,is_active)",
        "order": "sort_order.asc"})
    r.raise_for_status()
    return r.json()


def plan(products: list[dict]) -> list[dict]:
    rows = []
    for p in products:
        if not p["is_active"] or p["slug"] in EXCLUDED:
            continue
        v = next((v for v in p["store_variants"] if v["kind"] == "print" and v["is_active"]), None)
        if not v or not v["page_count"]:
            raise SystemExit(f"{p['slug']}: no active print variant with a page count")
        rows.append({"slug": p["slug"], "variant_id": v["id"], "pages": v["page_count"],
                     "old": v["price_bdt"], "new": price_for(v["page_count"])})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    products = load()
    rows = plan(products)
    print(f"{'book':28} {'pages':>5} {'sheets':>6} {'cost':>8} {'old':>6} {'new':>6}")
    for r in rows:
        print(f"{r['slug']:28} {r['pages']:>5} {sheets_for(r['pages']):>6} {cost_for(r['pages']):>8.1f} {r['old']:>6} {r['new']:>6}")
    print(f"{len(rows)} books repriced; excluded: {', '.join(sorted(EXCLUDED))}")
    if not args.commit:
        print("Dry run. Use --commit to write.")
        return

    BACKUP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H%M%S")
    (BACKUP / f"store_products_{stamp}.json").write_text(json.dumps(products, indent=2), encoding="utf-8")
    print(f"Backup: {BACKUP}")

    now = datetime.now(timezone.utc).isoformat()
    for r in rows:
        resp = requests.patch(f"{SUPABASE_URL}/rest/v1/store_variants",
                              params={"id": f"eq.{r['variant_id']}", "price_bdt": f"eq.{r['old']}"},
                              json={"price_bdt": r["new"], "updated_at": now},
                              headers={**headers(), "Prefer": "return=representation"}, timeout=60)
        resp.raise_for_status()
        if len(resp.json()) != 1:
            raise RuntimeError(f"{r['slug']}: price changed since it was read; stopped")

    after = {p["slug"]: p for p in load()}
    for r in rows:
        v = next(v for v in after[r["slug"]]["store_variants"] if v["id"] == r["variant_id"])
        assert v["price_bdt"] == r["new"], r["slug"]
    print(f"Verified {len(rows)} prices from a fresh read.")


if __name__ == "__main__":
    main()
