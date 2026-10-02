#!/usr/bin/env python3
"""Put the printed workbooks on sale: covers, previews, page counts, activation.

WHAT IS SOLD -- two products:
  * Mathematics B, sold as ONE bundle of both volumes (Part 1 + Part 2). The
    separate Part 1 and Part 2 listings are retired (is_active = false) once the
    bundle is published; their rows, and every order placed against them, stay.
  * Further Pure Mathematics, on its own.

The bundle row is created on the first --commit if it does not exist yet, with
its fields copied from the Part 1 listing and its price from --bundle-price.

The store schema, the catalogue rows and the order machinery already exist
(migrations 21-26). What the products lack is the material a buyer needs to see
before paying: a cover image and a sample of the inside. This produces both from
the delivered print masters and switches the products on.

For each product it:
  * renders page 1 of the questions volume -- which IS the front cover, per the
    PRINT_SPEC files -- to a JPEG, and uploads it as the shop cover;
  * extracts the first N pages (`preview_pages` on the product row) into a
    preview PDF and uploads that;
  * measures the real page count of the questions volume and writes it to the
    printed variant, so the listing quotes a measured figure rather than a claim;
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

# What is actually sold: the questions volumes only. The mark-scheme volumes are
# built and kept alongside them, but they are NOT part of the product and must
# not appear in the page count, the spec line or the description.
MATHSB_PART1 = WORKBOOK / "mathsb/print/final/Mathematics_B_Workbook_PRINT_Part1.pdf"
MATHSB_PART2 = WORKBOOK / "mathsb/print/final/Mathematics_B_Workbook_PRINT_Part2.pdf"
FPM = WORKBOOK / "fpm/print/final/Further_Pure_Mathematics_Workbook_PRINT.pdf"

# slug -> the questions volume(s) the product ships, in reading order.
PRODUCTS = {
    "mathematics-b-complete": [MATHSB_PART1, MATHSB_PART2],
    "further-pure-mathematics": [FPM],
}

# A product row that may not exist yet is created from a template listing.
BUNDLE_SLUG = "mathematics-b-complete"
BUNDLE_TEMPLATE_SLUG = "mathematics-b-part-1"
BUNDLE_TITLE = "Mathematics B — Part 1 & Part 2"
BUNDLE_SUBTITLE = "The complete chapterwise workbook, both volumes"

# Listings replaced by the bundle. Switched off only after it is live, so the
# shop is never left without a Mathematics B book.
RETIRED_SLUGS = ["mathematics-b-part-1", "mathematics-b-part-2"]

# Copy that must not promise a mark scheme. Keyed by slug; `{pp}` is filled with
# the measured page count of the questions volume.
COPY = {
    BUNDLE_SLUG: {
        "spec_summary": "2 books · {pp} pages of questions",
        "description":
            "The complete Mathematics B chapterwise workbook in two spiral-bound volumes. "
            "Part 1 covers chapters 1 to 5 — Number, Sets, Algebra, Functions and Matrices; "
            "Part 2 covers chapters 6 to 11 — Geometry, Mensuration, Vectors and "
            "transformation geometry, and the rest of the specification. Every past-paper "
            "question is regrouped chapter by chapter and section by section, so you "
            "practise one skill until it is finished instead of meeting it once per paper. "
            "Reproduced at 1:1 from the board's own sheets, so the ruled answer lines and "
            "the original spacing are intact. Each volume has its own contents, "
            "summary-and-formulae section and question index.",
    },
    "further-pure-mathematics": {
        "spec_summary": "{pp} pages of questions",
        "description":
            "The whole of Further Pure Mathematics, every past-paper question sorted into the "
            "specification's own chapter order — logarithms and indices, the quadratic "
            "function, identities and inequalities, graphs, series, the binomial series, "
            "vectors, coordinate geometry, calculus and trigonometry. Recurring question "
            "shapes are clustered together on purpose: meeting the same archetype four times "
            "in four papers' clothing is how pattern recognition gets built.",
    },
}

PRINT_VARIANT_LABEL = "Printed copy — spiral bound"
BUNDLE_VARIANT_LABEL = "Printed set — 2 spiral-bound books"

COVER_DPI = 150
DEFAULT_PREVIEW_PAGES = 12


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
                        region_name="auto", config=Config(retries={"max_attempts": 3}))


def render_cover(volumes: list[Path]) -> bytes:
    """Page 1 of a print master is the front cover (see PRINT_SPEC.md).

    A set of books is drawn as a stack on an A4-portrait canvas -- later volumes
    behind and up to the right, Part 1 in front -- because the shop frames every
    cover in a 210:297 box and would crop a side-by-side image to its middle.
    """
    if len(volumes) == 1:
        with fitz.open(volumes[0]) as doc:
            pix = doc[0].get_pixmap(dpi=COVER_DPI, colorspace=fitz.csRGB)
            return pix.tobytes("jpeg", jpg_quality=88)

    W, H = fitz.paper_size("a4")
    scale = 0.74
    margin = 0.04 * W
    out = fitz.open()
    canvas = out.new_page(width=W, height=H)
    canvas.draw_rect(canvas.rect, color=None, fill=(0.95, 0.95, 0.96))
    n = len(volumes)
    w, h = W * scale, H * scale
    step_x = (W - w - 2 * margin) / (n - 1)
    step_y = (H - h - 2 * margin) / (n - 1)
    # Back to front: the last volume is drawn first, top right.
    for i in reversed(range(n)):
        x = margin + i * step_x
        y = margin + (n - 1 - i) * step_y
        rect = fitz.Rect(x, y, x + w, y + h)
        shadow = fitz.Rect(rect.x0 + 4, rect.y0 + 4, rect.x1 + 4, rect.y1 + 4)
        canvas.draw_rect(shadow, color=None, fill=(0.75, 0.75, 0.78))
        with fitz.open(volumes[i]) as doc:
            canvas.show_pdf_page(rect, doc, 0, keep_proportion=True)
        canvas.draw_rect(rect, color=(0.6, 0.6, 0.65), width=0.6)
    pix = canvas.get_pixmap(dpi=COVER_DPI, colorspace=fitz.csRGB)
    out.close()
    return pix.tobytes("jpeg", jpg_quality=88)


def build_preview(volumes: list[Path], pages: int) -> tuple[bytes, int]:
    """The first `pages` sheets, cover included, split evenly across volumes."""
    per_volume = max(1, -(-pages // len(volumes)))  # ceiling division
    out = fitz.open()
    for pdf_path in volumes:
        with fitz.open(pdf_path) as src:
            n = min(per_volume, len(src))
            out.insert_pdf(src, from_page=0, to_page=n - 1)
    total = len(out)
    data = out.tobytes(garbage=3, deflate=True)
    out.close()
    return data, total


def page_count(volumes: list[Path]) -> int:
    total = 0
    for pdf_path in volumes:
        with fitz.open(pdf_path) as doc:
            total += len(doc)
    return total


def fetch_products() -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/store_products", headers=H, timeout=60,
                     params={"select": "id,slug,title,subtitle,description,subject_code,spec_summary,"
                                       "preview_pages,is_active,cover_image_url,preview_r2_key,sort_order",
                             "order": "sort_order"})
    r.raise_for_status()
    return r.json()


def fetch_variants(product_id: str) -> list[dict]:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/store_variants", headers=H, timeout=60,
                     params={"select": "id,kind,label,price_bdt,compare_at_bdt,stock_qty,allow_cod,"
                                       "page_count,is_active",
                             "product_id": f"eq.{product_id}"})
    r.raise_for_status()
    return r.json()


def patch(table: str, row_id: str, payload: dict) -> None:
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers={**H, "Content-Type": "application/json"},
                       params={"id": f"eq.{row_id}"}, json=payload, timeout=60)
    r.raise_for_status()


def insert(table: str, payload: dict) -> dict:
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}",
                      headers={**H, "Content-Type": "application/json", "Prefer": "return=representation"},
                      json=payload, timeout=60)
    if not r.ok:
        raise SystemExit(f"!! could not insert into {table}: {r.status_code} {r.text}")
    return r.json()[0]


def create_bundle(products: dict, bundle_price: int, stock: int) -> dict:
    """Create the Mathematics B bundle from the Part 1 listing, inactive.

    Only the columns the shop is known to use are copied. If the table has a
    required column this does not know about, the insert fails loudly and
    nothing is half-created.
    """
    template = products.get(BUNDLE_TEMPLATE_SLUG)
    if not template:
        raise SystemExit(f"!! cannot create {BUNDLE_SLUG}: template {BUNDLE_TEMPLATE_SLUG} not found")
    product = insert("store_products", {
        "slug": BUNDLE_SLUG,
        "title": BUNDLE_TITLE,
        "subtitle": BUNDLE_SUBTITLE,
        "subject_code": template.get("subject_code"),
        "sort_order": template.get("sort_order") or 0,
        "preview_pages": template.get("preview_pages") or DEFAULT_PREVIEW_PAGES,
        "is_active": False,  # switched on below, once its cover and preview exist
    })

    parts = [products[s] for s in RETIRED_SLUGS if s in products]
    separate_total = 0
    for part in parts:
        for v in fetch_variants(part["id"]):
            if v["kind"] == "print":
                separate_total += v["price_bdt"]
    template_print = next((v for v in fetch_variants(template["id"]) if v["kind"] == "print"), {})
    insert("store_variants", {
        "product_id": product["id"],
        "kind": "print",
        "label": BUNDLE_VARIANT_LABEL,
        "price_bdt": bundle_price,
        # Show the saving only when there is one.
        "compare_at_bdt": separate_total if separate_total > bundle_price else None,
        "stock_qty": stock,
        "allow_cod": template_print.get("allow_cod", True),
        "is_active": True,
    })
    return product


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
    ap.add_argument("--bundle-price", type=int, default=1200,
                    help="price in BDT for the Mathematics B Part 1 + Part 2 set, used only "
                         "when the bundle is first created (default 1200 = the two parts' "
                         "current 600 each); change it later from the admin portal")
    args = ap.parse_args()

    products = {p["slug"]: p for p in fetch_products()}
    r2 = get_r2() if args.commit else None
    print(f"{'COMMIT' if args.commit else 'dry-run'} — {len(PRODUCTS)} products\n")

    activated = 0
    published: set[str] = set()
    for slug, volumes in PRODUCTS.items():
        missing = [v.name for v in volumes if not v.exists()]
        if missing:
            print(f"!! {slug}: missing {', '.join(missing)} — skipping")
            continue
        product = products.get(slug)
        if not product:
            if slug != BUNDLE_SLUG:
                print(f"!! {slug}: no such product row — skipping")
                continue
            if not args.commit:
                print(f"=== {slug}: would CREATE from {BUNDLE_TEMPLATE_SLUG} as {BUNDLE_TITLE!r}, "
                      f"{BUNDLE_VARIANT_LABEL!r} at {args.bundle_price} BDT")
                product = {**products.get(BUNDLE_TEMPLATE_SLUG, {}), "id": "(new)", "slug": slug}
            else:
                product = create_bundle(products, args.bundle_price, args.stock)
                print(f"=== {slug}: created ({BUNDLE_TITLE}, {args.bundle_price} BDT)")

        q_pages = page_count(volumes)
        want_preview = product.get("preview_pages") or DEFAULT_PREVIEW_PAGES
        cover = render_cover(volumes)
        preview, preview_n = build_preview(volumes, want_preview)
        is_set = len(volumes) > 1
        variant_label = BUNDLE_VARIANT_LABEL if is_set else PRINT_VARIANT_LABEL

        cover_key = f"store/{slug}/cover.jpg"
        preview_key = f"store/{slug}/preview.pdf"
        cover_url = f"{R2_PUBLIC_URL}/{cover_key}"

        copy = COPY[slug]
        spec = copy["spec_summary"].format(pp=q_pages)
        print(f"=== {slug}")
        print(f"    questions volume: {q_pages}pp (mark schemes are not sold and are excluded)")
        print(f"    spec line: {spec}")
        print(f"    cover   {len(cover)//1024:>5} KB -> {cover_key}")
        print(f"    preview {len(preview)//1024:>5} KB, {preview_n} pages -> {preview_key}")
        print(f"    printed variant: page_count {q_pages}, stock_qty -> {args.stock}, "
              f"label {variant_label!r}")

        if not args.commit:
            print("    would activate the product and set the printed variant's page count\n")
            continue

        r2.put_object(Bucket=R2_BUCKET, Key=cover_key, Body=cover, ContentType="image/jpeg")
        r2.put_object(Bucket=R2_BUCKET, Key=preview_key, Body=preview, ContentType="application/pdf")
        patch("store_products", product["id"], {
            "cover_image_url": cover_url,
            "preview_r2_key": preview_key,
            "preview_pages": preview_n,
            "spec_summary": spec,
            "description": copy["description"],
            **({"title": BUNDLE_TITLE, "subtitle": BUNDLE_SUBTITLE} if is_set else {}),
            "is_active": True,
        })
        for v in fetch_variants(product["id"]):
            if v["kind"] == "print":
                # stock_qty is seeded at 0, and pricing.ts refuses any line where
                # stock is below the quantity ordered -- so without this every
                # order would come back "out of stock".
                patch("store_variants", v["id"], {
                    "page_count": q_pages,
                    "stock_qty": args.stock,
                    "label": variant_label,
                })
        activated += 1
        published.add(slug)
        print("    published\n")

    # Retire the separate Mathematics B parts, but only once the bundle that
    # replaces them is live. Rows and past orders are kept; they just stop
    # being listed or orderable.
    for slug in RETIRED_SLUGS:
        row = products.get(slug)
        if not row:
            continue
        if not args.commit:
            print(f"=== {slug}: would RETIRE (is_active -> false) once {BUNDLE_SLUG} is published")
        elif BUNDLE_SLUG in published:
            patch("store_products", row["id"], {"is_active": False})
            print(f"=== {slug}: retired — sold only as part of {BUNDLE_SLUG} now")
        else:
            print(f"!! {slug}: left on sale, because {BUNDLE_SLUG} was not published")

    if args.commit:
        print(f"activated {activated} product(s)")
        if args.enable_store:
            set_setting("store_enabled", "true")
            print("store_enabled = true — the shop is now open")
        else:
            print("store_enabled left as-is; pass --enable-store to open the shop")


if __name__ == "__main__":
    main()
