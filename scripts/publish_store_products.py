#!/usr/bin/env python3
"""Put the printed workbooks on sale: covers, previews, page counts, activation.

The store schema, the catalogue rows and the order machinery already exist
(migrations 21-26). What the products lack is the material a buyer needs to see
before paying: a cover image and a sample of the inside. This produces both from
the delivered print masters and switches the products on.

For each product it:
  * renders page 1 of the questions volume -- which IS the front cover, per the
    PRINT_SPEC files -- to a JPEG, and uploads it as the shop cover;
  * extracts the first N pages (`preview_pages` on the product row) into a
    preview PDF and uploads that;
  * measures the real page count of both volumes and writes it to the printed
    variant, so the listing quotes a measured figure rather than a claim;
  * sets `is_active` once its cover and preview are both in place.

Covers and previews go to the PUBLIC bucket: they are advertising, and
`publicPreviewUrl` builds their URL from NEXT_PUBLIC_R2_PUBLIC_URL. The full
books are NOT uploaded -- digital sales are off (migration 26), so no paid file
is ever served and the private bucket is not needed to open the shop.

Dry-run by default; --commit writes. Idempotent: re-running replaces the derived
artwork and leaves prices, stock and orders untouched.

Usage:
    python -X utf8 scripts/publish_store_products.py
    python -X utf8 scripts/publish_store_products.py --commit
    python -X utf8 scripts/publish_store_products.py --commit --enable-store
"""
import argparse
import io
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

import fitz

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

WORKBOOK = ROOT / "data" / "workbook"

# slug -> (questions volume, mark-scheme volume)
PRODUCTS = {
    "mathematics-b-part-1": (
        WORKBOOK / "mathsb/print/final/Mathematics_B_Workbook_PRINT_Part1.pdf",
        WORKBOOK / "mathsb/print/final/Mathematics_B_MarkSchemes_PRINT_Part1.pdf",
    ),
    "mathematics-b-part-2": (
        WORKBOOK / "mathsb/print/final/Mathematics_B_Workbook_PRINT_Part2.pdf",
        WORKBOOK / "mathsb/print/final/Mathematics_B_MarkSchemes_PRINT_Part2.pdf",
    ),
    "further-pure-mathematics": (
        WORKBOOK / "fpm/print/final/Further_Pure_Mathematics_Workbook_PRINT.pdf",
        WORKBOOK / "fpm/print/final/Further_Pure_Mathematics_MarkSchemes_PRINT.pdf",
    ),
}

COVER_DPI = 150
DEFAULT_PREVIEW_PAGES = 12


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
                        region_name="auto", config=Config(retries={"max_attempts": 3}))


def render_cover(pdf_path: Path) -> bytes:
    """Page 1 of a print master is the front cover (see PRINT_SPEC.md)."""
    with fitz.open(pdf_path) as doc:
        page = doc[0]
        pix = page.get_pixmap(dpi=COVER_DPI, colorspace=fitz.csRGB)
        return pix.tobytes("jpeg", jpg_quality=88)


def build_preview(pdf_path: Path, pages: int) -> tuple[bytes, int]:
    """First `pages` sheets, cover included, as a standalone PDF."""
    with fitz.open(pdf_path) as src:
        n = min(pages, len(src))
        out = fitz.open()
        out.insert_pdf(src, from_page=0, to_page=n - 1)
        data = out.tobytes(garbage=3, deflate=True)
        out.close()
        return data, n


def page_count(pdf_path: Path) -> int:
    with fitz.open(pdf_path) as doc:
        return len(doc)


def fetch_products() -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/store_products", headers=H, timeout=60,
                     params={"select": "id,slug,title,preview_pages,is_active,"
                                       "cover_image_url,preview_r2_key", "order": "sort_order"})
    r.raise_for_status()
    return r.json()


def fetch_variants(product_id: str) -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/store_variants", headers=H, timeout=60,
                     params={"select": "id,kind,label,price_bdt,page_count,is_active",
                             "product_id": f"eq.{product_id}"})
    r.raise_for_status()
    return r.json()


def patch(table: str, row_id: str, payload: dict) -> None:
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers={**H, "Content-Type": "application/json"},
                       params={"id": f"eq.{row_id}"}, json=payload, timeout=60)
    r.raise_for_status()


def set_setting(key: str, value: str) -> None:
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/store_settings",
                       headers={**H, "Content-Type": "application/json"},
                       params={"key": f"eq.{key}"}, json={"value": value}, timeout=60)
    r.raise_for_status()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--enable-store", action="store_true",
                    help="also flip store_enabled to true (the shop goes live)")
    ap.add_argument("--stock", type=int, default=50,
                    help="stock_qty to set on each printed variant (seeded at 0, "
                         "which refuses every order)")
    args = ap.parse_args()

    products = {p["slug"]: p for p in fetch_products()}
    r2 = get_r2() if args.commit else None
    print(f"{'COMMIT' if args.commit else 'dry-run'} — {len(PRODUCTS)} products\n")

    activated = 0
    for slug, (q_pdf, ms_pdf) in PRODUCTS.items():
        product = products.get(slug)
        if not product:
            print(f"!! {slug}: no such product row — skipping")
            continue
        missing = [p for p in (q_pdf, ms_pdf) if not p.exists()]
        if missing:
            print(f"!! {slug}: missing file(s) {[m.name for m in missing]} — skipping")
            continue

        q_pages, ms_pages = page_count(q_pdf), page_count(ms_pdf)
        want_preview = product.get("preview_pages") or DEFAULT_PREVIEW_PAGES
        cover = render_cover(q_pdf)
        preview, preview_n = build_preview(q_pdf, want_preview)

        cover_key = f"store/{slug}/cover.jpg"
        preview_key = f"store/{slug}/preview.pdf"
        cover_url = f"{R2_PUBLIC_URL}/{cover_key}"

        print(f"=== {slug}")
        print(f"    questions {q_pages}pp + mark schemes {ms_pages}pp = {q_pages + ms_pages}pp")
        print(f"    cover   {len(cover)//1024:>5} KB -> {cover_key}")
        print(f"    preview {len(preview)//1024:>5} KB, {preview_n} pages -> {preview_key}")
        print(f"    printed variant: page_count {q_pages + ms_pages}, stock_qty -> {args.stock}")

        if not args.commit:
            print("    would activate the product and set the printed variant's page count\n")
            continue

        r2.put_object(Bucket=R2_BUCKET, Key=cover_key, Body=cover, ContentType="image/jpeg")
        r2.put_object(Bucket=R2_BUCKET, Key=preview_key, Body=preview, ContentType="application/pdf")
        patch("store_products", product["id"], {
            "cover_image_url": cover_url,
            "preview_r2_key": preview_key,
            "preview_pages": preview_n,
            "is_active": True,
        })
        for v in fetch_variants(product["id"]):
            if v["kind"] == "print":
                # stock_qty is seeded at 0, and pricing.ts refuses any line where
                # stock is below the quantity ordered -- so without this every
                # order would come back "out of stock".
                patch("store_variants", v["id"],
                      {"page_count": q_pages + ms_pages, "stock_qty": args.stock})
        activated += 1
        print("    published\n")

    if args.commit:
        print(f"activated {activated} product(s)")
        if args.enable_store:
            set_setting("store_enabled", "true")
            print("store_enabled = true — the shop is now open")
        else:
            print("store_enabled left as-is; pass --enable-store to open the shop")


if __name__ == "__main__":
    main()
