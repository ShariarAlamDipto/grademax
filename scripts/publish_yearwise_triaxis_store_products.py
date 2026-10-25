#!/usr/bin/env python3
"""List the 50 Tri Axis yearwise question booklets in the GradeMax store, ready for pricing.

Each book in output/pdf/GradeMax_Yearwise_2026_TriAxis/Books becomes a store
product with its front cover (JPEG) and a free preview (the opening pages: cover,
title sheet, contents and the first paper), both on the public R2 bucket.

Prices are set by the admin (user, 21 Oct 2026). So a NEW listing is created
HIDDEN, with a printed variant at price 0 and stock 0; the admin page refuses to
put it on sale until a price is set. An EXISTING listing (same slug) only has its
copy, cover and preview refreshed -- its price, stock and on-sale switch are the
admin's and are never touched.

Read-only until --commit. Before writing, the current store rows are backed up to
data/backups/store_yearwise_triaxis_<date>/.

    python -X utf8 scripts/publish_yearwise_triaxis_store_products.py            # dry run
    python -X utf8 scripts/publish_yearwise_triaxis_store_products.py --commit
    ... --only WPH11 4MA1F
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import fitz
import requests

import publish_store_products as store

ROOT = store.ROOT
BOOKS = ROOT / "output/pdf/GradeMax_Yearwise_2026_TriAxis/Books"
BACKUP = ROOT / "data/backups" / f"store_yearwise_triaxis_{date.today().isoformat()}"
PREVIEW_PAGES = 20
SORT_START = 100

# Book code -> (store title, Pearson code printed on the book, level, subject group).
TITLES = {
    "4MA1": ("Mathematics A (Higher)", "4MA1", "IGCSE", "Mathematics"),
    "4MA1F": ("Mathematics A (Foundation)", "4MA1", "IGCSE", "Mathematics"),
    "4MB1": ("Mathematics B", "4MB1", "IGCSE", "Mathematics"),
    "4PM1": ("Further Pure Mathematics", "4PM1", "IGCSE", "Mathematics"),
    "4PH1": ("Physics", "4PH1", "IGCSE", "Sciences"),
    "4CH1": ("Chemistry", "4CH1", "IGCSE", "Sciences"),
    "4BI1": ("Biology", "4BI1", "IGCSE", "Sciences"),
    "4HB1": ("Human Biology", "4HB1", "IGCSE", "Sciences"),
    "4AC1": ("Accounting", "4AC1", "IGCSE", "Business and humanities"),
    "4BS1": ("Business", "4BS1", "IGCSE", "Business and humanities"),
    "4EC1": ("Economics", "4EC1", "IGCSE", "Business and humanities"),
    "4EB1": ("English Language B", "4EB1", "IGCSE", "Business and humanities"),
    "4IT1": ("ICT (Paper 1)", "4IT1", "IGCSE", "Computing"),
    "4CP0": ("Computer Science (Paper 1)", "4CP0", "IGCSE", "Computing"),
    **{f"WMA1{n}": (f"Pure Mathematics P{n}", f"WMA1{n}", "IAL", "Mathematics") for n in range(1, 5)},
    "WFM01": ("Further Pure Mathematics FP1", "WFM01", "IAL", "Mathematics"),
    "WFM02": ("Further Pure Mathematics FP2", "WFM02", "IAL", "Mathematics"),
    "WFM03": ("Further Pure Mathematics FP3", "WFM03", "IAL", "Mathematics"),
    "WME01": ("Mechanics M1", "WME01", "IAL", "Mathematics"),
    "WME02": ("Mechanics M2", "WME02", "IAL", "Mathematics"),
    "WME03": ("Mechanics M3", "WME03", "IAL", "Mathematics"),
    "WST01": ("Statistics S1", "WST01", "IAL", "Mathematics"),
    "WST02": ("Statistics S2", "WST02", "IAL", "Mathematics"),
    "WST03": ("Statistics S3", "WST03", "IAL", "Mathematics"),
    "WDM11": ("Decision Mathematics D1", "WDM11", "IAL", "Mathematics"),
    **{f"WPH1{n}": (f"Physics Unit {n}", f"WPH1{n}", "IAL", "Physics") for n in range(1, 7)},
    **{f"WCH1{n}": (f"Chemistry Unit {n}", f"WCH1{n}", "IAL", "Chemistry") for n in range(1, 7)},
    **{f"WBI1{n}": (f"Biology Unit {n}", f"WBI1{n}", "IAL", "Biology") for n in range(1, 7)},
    **{f"WEC1{n}": (f"Economics Unit {n}", f"WEC1{n}", "IAL", "Economics") for n in range(1, 5)},
}
SESSION = re.compile(r"^(January|May/June|October/November) (20\d\d) \|")
SEASON_WORD = {"IGCSE": {"January": "January", "May/June": "June", "October/November": "November"},
               "IAL": {"January": "January", "May/June": "June", "October/November": "October"}}
BOARD = {"IGCSE": "Edexcel International GCSE", "IAL": "Edexcel International A Level"}


def api(method: str, table: str, *, params: dict, payload: dict | None = None) -> list[dict]:
    response = requests.request(
        method, f"{store.SUPABASE_URL}/rest/v1/{table}",
        headers={**store.H, "Content-Type": "application/json", "Prefer": "return=representation"},
        params=params, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def read_book(path: Path) -> dict:
    """Everything the listing says comes from the finished book itself."""
    code = path.name.split("_")[1]
    title, printed, level, group = TITLES[code]
    with fitz.open(path) as doc:
        pages = len(doc)
        sessions = []
        papers = 0
        for lvl, text, _ in doc.get_toc():
            m = SESSION.match(text)
            if lvl == 3 and m:
                papers += 1
                label = f"{SEASON_WORD[level][m.group(1)]} {m.group(2)}"
                if label not in sessions:
                    sessions.append(label)
        if not sessions:
            raise ValueError(f"{path.name}: no paper bookmarks")
        if "YEAR-WISE QUESTION PAPER" not in doc[0].get_text().upper().replace("YEAR WISE", "YEAR-WISE"):
            raise ValueError(f"{path.name}: page 1 is not the Tri Axis front cover")
    span = f"{sessions[0]} – {sessions[-1]}"
    is_maths = group == "Mathematics"
    layout = ("Each question keeps its original pages and at most one spare answer page, so the book "
              "stays compact." if is_maths else "Every paper keeps the board's original layout and answer space.")
    return {
        "code": code, "path": path, "level": level, "group": group,
        "slug": f"{code.lower()}-yearwise-2026",
        "title": f"{title} — Yearwise Question Booklet",
        "subtitle": f"{BOARD[level]} {printed} · {span}",
        "subject_code": printed,
        "description": (
            f"Every {title} question paper from {sessions[0]} to {sessions[-1]}: {papers} papers across "
            f"{len(sessions)} exam sessions, in the order they were sat. {layout} "
            "Question papers only; mark schemes are free in the subject's lecture section on GradeMax. "
            "Spiral-bound printed booklet, delivered anywhere in Bangladesh."),
        "spec_summary": f"{papers} papers · {len(sessions)} sessions · {pages} pages",
        "page_count": pages,
    }


def prepare(only: set[str] | None) -> list[dict]:
    books = [read_book(p) for p in sorted(BOOKS.glob("GradeMax_*_Yearwise_Questions_*.pdf"))
             if not only or p.name.split("_")[1] in only]
    level_rank = {"IGCSE": 0, "IAL": 1}
    order = sorted(books, key=lambda b: (level_rank[b["level"]], b["group"], b["code"]))
    for i, book in enumerate(order):
        book["sort_order"] = SORT_START + i
        book["cover"] = store.render_cover(book["path"])
        book["preview"], book["preview_pages"] = store.build_preview([book["path"]], PREVIEW_PAGES)
        book["cover_key"] = f"store/{book['slug']}/cover.jpg"
        book["preview_key"] = f"store/{book['slug']}/preview.pdf"
    return order


def backup() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    rows = api("GET", "store_products", params={
        "select": "*,store_variants(id,product_id,kind,label,price_bdt,stock_qty,page_count,allow_cod,is_active)"})
    (BACKUP / "store_products_before.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(f"backed up {len(rows)} products -> {BACKUP.relative_to(ROOT)}")


def publish(book: dict, r2) -> str:
    for key, body, mime in ((book["cover_key"], book["cover"], "image/jpeg"),
                            (book["preview_key"], book["preview"], "application/pdf")):
        r2.put_object(Bucket=store.R2_BUCKET, Key=key, Body=body, ContentType=mime)
        got = requests.get(f"{store.R2_PUBLIC_URL}/{key}", timeout=60)
        got.raise_for_status()
        if got.content != body:
            raise ValueError(f"public asset does not match the upload: {key}")
    copy = {k: book[k] for k in ("slug", "title", "subtitle", "description", "subject_code",
                                 "spec_summary", "sort_order", "preview_pages")}
    copy.update({"cover_image_url": f"{store.R2_PUBLIC_URL}/{book['cover_key']}",
                 "preview_r2_key": book["preview_key"],
                 "updated_at": datetime.now(timezone.utc).isoformat()})
    existing = api("GET", "store_products", params={"slug": f"eq.{book['slug']}", "select": "id,is_active"})
    if existing:
        product_id = existing[0]["id"]
        copy.pop("sort_order")      # the admin may have reordered it
        api("PATCH", "store_products", params={"id": f"eq.{product_id}"}, payload=copy)
        variants = api("GET", "store_variants", params={"product_id": f"eq.{product_id}", "kind": "eq.print",
                                                         "select": "id"})
        for v in variants:          # the page count follows the book; price and stock stay the admin's
            api("PATCH", "store_variants", params={"id": f"eq.{v['id']}"},
                payload={"page_count": book["page_count"], "updated_at": copy["updated_at"]})
        action = "refreshed"
    else:
        product_id = api("POST", "store_products", params={}, payload={**copy, "is_active": False})[0]["id"]
        api("POST", "store_variants", params={}, payload={
            "product_id": product_id, "kind": "print", "label": store.PRINT_VARIANT_LABEL,
            "price_bdt": 0, "stock_qty": 0, "page_count": book["page_count"], "allow_cod": True,
            "is_active": True, "updated_at": copy["updated_at"]})
        action = "created hidden, price 0"
    row = api("GET", "store_products", params={
        "id": f"eq.{product_id}", "select": "slug,is_active,cover_image_url,preview_r2_key,"
                                            "store_variants(kind,price_bdt,page_count)"})[0]
    assert row["preview_r2_key"] == book["preview_key"] and row["cover_image_url"].endswith(book["cover_key"])
    assert any(v["kind"] == "print" and v["page_count"] == book["page_count"] for v in row["store_variants"])
    if action.startswith("created"):
        assert row["is_active"] is False
    return action


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--only", nargs="*", help="book codes, e.g. WPH11 4MA1F")
    args = ap.parse_args()
    if not store.R2_PUBLIC_URL:
        ap.error("NEXT_PUBLIC_R2_PUBLIC_URL is required")
    books = prepare(set(args.only) if args.only else None)
    existing = {r["slug"] for r in api("GET", "store_products", params={"select": "slug"})}
    for b in books:
        state = "exists: refresh copy/cover/preview only" if b["slug"] in existing else "new: hidden, price 0"
        print(f"{b['sort_order']} {b['slug']:24} {b['spec_summary']:38} preview {b['preview_pages']}pp "
              f"cover {len(b['cover']) // 1024}KB  [{state}]")
    if not args.commit:
        print(f"Dry run: {len(books)} listings. Use --commit to publish.")
        return
    backup()
    r2 = store.get_r2()
    for b in books:
        print(f"  {b['slug']}: {publish(b, r2)}", flush=True)
    print(f"Published {len(books)} listings. Set prices and switch them on in Admin → Store → Products.")


if __name__ == "__main__":
    main()
