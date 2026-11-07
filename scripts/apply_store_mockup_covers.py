#!/usr/bin/env python3
"""Publish the mockup covers and put the hidden Tri Axis yearwise booklets on sale.

1. Uploads output/store_covers_mockup/<slug>.jpg to R2 as store/<slug>/<COVER_FILE>
   (a new key, so no CDN or next/image cache keeps serving the old cover), then
   checks that the public URL returns exactly those bytes.
2. Points store_products.cover_image_url at it (guarded on the old URL).
3. For the listings chosen in store_cover_targets.py: print variant price 0 -> 600,
   stock 0 -> 50 (guarded on the old values), then is_active false -> true.

Dry run by default. --commit backs up every store row to data/backups first and
re-reads each row after writing.

    python -X utf8 scripts/design_store_mockup_covers.py
    python -X utf8 scripts/apply_store_mockup_covers.py            # dry run
    python -X utf8 scripts/apply_store_mockup_covers.py --commit
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone

import requests

import publish_store_products as store
from store_cover_targets import (NEW_PRICE_BDT, NEW_STOCK, ROOT, SUPABASE_URL, headers,
                                 is_to_switch_on, load_products, load_targets)

COVERS = ROOT / "output/store_covers_mockup"
# Bump the file name for every new design: covers are cached for a year, so the
# URL must change for buyers to see the new image. cover-photo = the ORIGINAL
# cover shown as a paperback on a matching backdrop (CoverIns reference).
# Retired: cover-mockup.jpg, cover-mockup-v2.jpg (redrawn covers, rejected 6 Nov 2026).
COVER_FILE = "cover-photo.jpg"
BACKUP = ROOT / "data/backups" / f"store_mockup_covers_{date.today().isoformat()}"


def patch(table: str, filters: dict, payload: dict) -> list[dict]:
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", params=filters, json=payload,
                       headers={**headers(), "Prefer": "return=representation"}, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if len(rows) != 1:
        raise RuntimeError(f"{table} {filters}: expected 1 row updated, got {len(rows)} (value changed?)")
    return rows


def upload_cover(r2, slug: str) -> str:
    body = (COVERS / f"{slug}.jpg").read_bytes()
    key = f"store/{slug}/{COVER_FILE}"
    r2.put_object(Bucket=store.R2_BUCKET, Key=key, Body=body, ContentType="image/jpeg",
                  CacheControl="public, max-age=31536000")
    url = f"{store.R2_PUBLIC_URL}/{key}"
    got = requests.get(url, timeout=60)
    if got.status_code != 200 or got.content != body:
        raise RuntimeError(f"public cover does not match the upload: {url}")
    return url


def apply(p: dict, r2, now: str) -> str:
    url = upload_cover(r2, p["slug"])
    old = p["cover_image_url"]
    patch("store_products",
          {"id": f"eq.{p['id']}", "cover_image_url": "is.null" if old is None else f"eq.{old}"},
          {"cover_image_url": url, "updated_at": now})
    action = "cover"
    if is_to_switch_on(p):
        v = next(v for v in p["store_variants"] if v["kind"] == "print")
        patch("store_variants",
              {"id": f"eq.{v['id']}", "price_bdt": "eq.0", "stock_qty": f"eq.{v['stock_qty']}"},
              {"price_bdt": NEW_PRICE_BDT, "stock_qty": max(v["stock_qty"] or 0, NEW_STOCK), "updated_at": now})
        patch("store_products", {"id": f"eq.{p['id']}", "is_active": "eq.false"},
              {"is_active": True, "updated_at": now})
        action = f"cover + {NEW_PRICE_BDT} BDT, stock {NEW_STOCK}, on sale"
    return action


def verify(expected: dict[str, bool]) -> None:
    rows = {p["slug"]: p for p in load_products()}
    for slug, switched in expected.items():
        p = rows[slug]
        assert p["is_active"], slug
        assert p["cover_image_url"].endswith(f"store/{slug}/{COVER_FILE}"), slug
        if switched:
            v = next(v for v in p["store_variants"] if v["kind"] == "print")
            assert v["price_bdt"] == NEW_PRICE_BDT and v["stock_qty"] >= NEW_STOCK and v["is_active"], slug
    print(f"Verified {len(expected)} listings from a fresh read.")


def restore_original(targets: list[dict], commit: bool) -> None:
    """Point each listing back at its original cover, store/<slug>/cover.jpg (still in R2)."""
    now = datetime.now(timezone.utc).isoformat()
    for p in targets:
        original = f"{store.R2_PUBLIC_URL}/store/{p['slug']}/cover.jpg"
        current = p["cover_image_url"] or ""
        if current == original:
            print(f"  {p['slug']:30} already original")
            continue
        if requests.head(original, timeout=60).status_code != 200:
            raise RuntimeError(f"original cover missing in R2: {original}")
        print(f"  {p['slug']:30} {current.rsplit('/', 1)[-1]} -> cover.jpg")
        if commit:
            patch("store_products", {"id": f"eq.{p['id']}", "cover_image_url": f"eq.{current}"},
                  {"cover_image_url": original, "updated_at": now})
    if commit:
        rows = {p["slug"]: p for p in load_products()}
        assert all(rows[p["slug"]]["cover_image_url"].endswith(f"store/{p['slug']}/cover.jpg") for p in targets)
        print(f"Verified {len(targets)} listings back on their original covers.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--restore-original", action="store_true",
                    help="put every listing back on its original store/<slug>/cover.jpg")
    args = ap.parse_args()

    targets = load_targets()
    if args.restore_original:
        if args.commit:
            BACKUP.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%H%M%S")
            (BACKUP / f"store_products_{stamp}.json").write_text(
                json.dumps(load_products(), indent=2), encoding="utf-8")
        restore_original(targets, args.commit)
        return
    missing = [p["slug"] for p in targets if not (COVERS / f"{p['slug']}.jpg").exists()]
    if missing:
        raise SystemExit(f"render covers first, missing: {missing}")
    switching = [p for p in targets if is_to_switch_on(p)]
    for p in targets:
        print(f"  {p['slug']:30} {'SWITCH ON at 600' if is_to_switch_on(p) else 'cover only'}")
    print(f"{len(targets)} covers, {len(switching)} listings to put on sale at {NEW_PRICE_BDT} BDT.")
    if not args.commit:
        print("Dry run. Use --commit to write.")
        return

    BACKUP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H%M%S")      # never overwrite an earlier run's backup
    (BACKUP / f"store_products_{stamp}.json").write_text(json.dumps(load_products(), indent=2), encoding="utf-8")
    print(f"Backup: {BACKUP}")

    r2 = store.get_r2()
    now = datetime.now(timezone.utc).isoformat()
    for p in targets:
        print(f"  {p['slug']}: {apply(p, r2, now)}", flush=True)
    verify({p["slug"]: is_to_switch_on(p) for p in targets})


if __name__ == "__main__":
    main()
