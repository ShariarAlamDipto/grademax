#!/usr/bin/env python3
"""Publish M1, S1 and P4 printed yearwise question booklets to Books.

Uses the finished GradeMax question volumes to produce public covers and
30-page previews. Full books and mark schemes stay local, as in the existing
print-only catalogue. Prices are M1 550 BDT, S1/P4 350 BDT.

Dry-run by default. --commit publishes; --stock sets available printed copies.
Without --stock, existing stock is preserved and new listings start at zero.

    python -X utf8 scripts/publish_yearwise_store_products.py
    python -X utf8 scripts/publish_yearwise_store_products.py --commit --stock 50
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import fitz
import requests

import publish_store_products as store


BOOKS = (
    ("m1", "Mechanics M1", "WME01", "January 2017 - October/November 2023", 550, 3),
    ("s1", "Statistics S1", "WST01", "January 2019 - October/November 2023", 350, 4),
    ("p4", "Pure Mathematics P4", "WMA14", "October/November 2020 - October/November 2023", 350, 5),
)
PREVIEW_PAGES = 30


def api(method: str, table: str, *, params: dict, payload: dict | None = None) -> list[dict]:
    response = requests.request(
        method, f"{store.SUPABASE_URL}/rest/v1/{table}",
        headers={**store.H, "Content-Type": "application/json", "Prefer": "return=representation"},
        params=params, json=payload, timeout=60,
    )
    response.raise_for_status()
    return response.json()


def prepare() -> list[dict]:
    """Prepare every asset before making any remote changes."""
    prepared = []
    for unit, title, code, sessions, price, order in BOOKS:
        slug = f"{unit}-yearwise"
        source = (store.WORKBOOK / f"{unit}_yearwise/final"
                  / f"GradeMax_{unit.upper()}_Yearwise_Workbook_GradeMax.pdf")
        with fitz.open(source) as doc:
            pages = len(doc)
            if "YEAR-WISE QUESTION PAPER" not in doc[0].get_text():
                raise ValueError(f"{source.name}: expected the final question-book cover")
        cover = store.render_cover(source)
        preview, preview_pages = store.build_preview([source], PREVIEW_PAGES)
        with fitz.open(stream=preview, filetype="pdf") as sample:
            for page in sample:
                pix = page.get_pixmap(matrix=fitz.Matrix(0.25, 0.25), colorspace=fitz.csGRAY)
                if min(pix.samples) >= 245:
                    raise ValueError(f"{slug}: blank sample page {page.number + 1}")
        prepared.append({
            "slug": slug, "title": f"{title} — Yearwise Question Booklet",
            "subtitle": f"Edexcel IAL {code} · {sessions}", "subject_code": code,
            "description": (
                f"{title} past question papers, arranged by year and exam session, "
                f"covering {sessions}. The board's original question layout and ruled "
                "answer space are retained, with surplus blank answer pages removed "
                "for a compact practice book. Spiral-bound printed question booklet, "
                "delivered anywhere in Bangladesh."
            ),
            "spec_summary": f"{pages} pages of yearwise questions",
            "sort_order": order, "page_count": pages, "price_bdt": price,
            "cover": cover, "preview": preview, "preview_pages": preview_pages,
            "cover_key": f"store/{slug}/cover.jpg",
            "preview_key": f"store/{slug}/preview.pdf",
        })
    return prepared


def publish(book: dict, r2, stock: int | None) -> None:
    # Upload and check the sample assets before a new listing is visible.
    for key, body, mime in (
        (book["cover_key"], book["cover"], "image/jpeg"),
        (book["preview_key"], book["preview"], "application/pdf"),
    ):
        r2.put_object(Bucket=store.R2_BUCKET, Key=key, Body=body, ContentType=mime)
        response = requests.get(f"{store.R2_PUBLIC_URL}/{key}", timeout=60)
        response.raise_for_status()
        if response.content != body:
            raise ValueError(f"Public asset does not match the upload: {key}")

    existing = api("GET", "store_products", params={"slug": f"eq.{book['slug']}", "select": "id"})
    product_copy = {key: book[key] for key in (
        "slug", "title", "subtitle", "description", "subject_code", "spec_summary", "sort_order", "preview_pages",
    )}
    product_copy.update({
        "cover_image_url": f"{store.R2_PUBLIC_URL}/{book['cover_key']}",
        "preview_r2_key": book["preview_key"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    if existing:
        product_id = existing[0]["id"]
        api("PATCH", "store_products", params={"id": f"eq.{product_id}"}, payload=product_copy)
    else:
        # New rows start inactive until their printed variant is registered.
        product_id = api("POST", "store_products", params={}, payload=product_copy)[0]["id"]

    existing_variants = api("GET", "store_variants", params={
        "product_id": f"eq.{product_id}", "kind": "eq.print", "select": "id,stock_qty",
    })
    variant = {
        "label": store.PRINT_VARIANT_LABEL, "price_bdt": book["price_bdt"],
        "page_count": book["page_count"], "allow_cod": True, "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if stock is not None:
        variant["stock_qty"] = stock
    if existing_variants:
        api("PATCH", "store_variants", params={"id": f"eq.{existing_variants[0]['id']}"}, payload=variant)
    else:
        variant.setdefault("stock_qty", 0)
        variant.update({"product_id": product_id, "kind": "print"})
        api("POST", "store_variants", params={}, payload=variant)
    api("PATCH", "store_products", params={"id": f"eq.{product_id}"}, payload={"is_active": True})

    result = api("GET", "store_products", params={
        "id": f"eq.{product_id}",
        "select": "slug,is_active,preview_pages,store_variants(kind,price_bdt,stock_qty,page_count,is_active)",
    })[0]
    printed = next(v for v in result["store_variants"] if v["kind"] == "print")
    assert result["is_active"] and printed["is_active"]
    assert printed["price_bdt"] == book["price_bdt"]
    assert printed["page_count"] == book["page_count"]
    assert result["preview_pages"] == book["preview_pages"]
    if stock is not None:
        assert printed["stock_qty"] == stock
    print("Published and verified:", json.dumps(result, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--stock", type=int, help="set stock of each printed booklet")
    args = parser.parse_args()
    if args.stock is not None and args.stock < 0:
        parser.error("--stock must be nonnegative")
    if not store.R2_PUBLIC_URL:
        parser.error("NEXT_PUBLIC_R2_PUBLIC_URL is required")
    books = prepare()
    for book in books:
        print(f"{book['slug']}: {book['page_count']}pp, BDT {book['price_bdt']}, "
              f"{book['preview_pages']}-page sample, cover {len(book['cover']) // 1024} KB, "
              f"sample {len(book['preview']) // 1024} KB")
    if not args.commit:
        print("Dry-run complete; use --commit to publish.")
        return
    r2 = store.get_r2()
    for book in books:
        publish(book, r2, args.stock)


if __name__ == "__main__":
    main()
