"""Which store listings get the new mockup covers and the 600 Taka price (6 Nov 2026).

Covers: every listing that is on sale now, plus the hidden Tri Axis yearwise
booklets being switched on.

Switched on at 600 Taka (stock 50): the Tri Axis yearwise booklets
(`*-yearwise-2026`) that are hidden at price 0. These three stay hidden because
older M1/S1/P4 listings are already on sale (the user chose no duplicates):
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local")
SUPABASE_URL = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""

NEW_PRICE_BDT = 600
NEW_STOCK = 50
KEEP_HIDDEN = {"wme01-yearwise-2026", "wst01-yearwise-2026", "wma14-yearwise-2026"}

COLUMNS = ("id,slug,title,subtitle,subject_code,is_active,sort_order,cover_image_url,"
           "store_variants(id,kind,price_bdt,stock_qty,is_active)")


def headers() -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SystemExit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env.local")
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def load_products() -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/store_products",
                     params={"select": COLUMNS, "order": "sort_order.asc"}, headers=headers(), timeout=60)
    r.raise_for_status()
    return r.json()


def is_to_switch_on(p: dict) -> bool:
    print_v = [v for v in p["store_variants"] if v["kind"] == "print"]
    return (not p["is_active"] and p["slug"].endswith("-yearwise-2026")
            and p["slug"] not in KEEP_HIDDEN and len(print_v) == 1 and print_v[0]["price_bdt"] == 0)


def load_targets() -> list[dict]:
    """Listings on sale now plus the ones being switched on, in catalogue order."""
    return [p for p in load_products() if p["is_active"] or is_to_switch_on(p)]
