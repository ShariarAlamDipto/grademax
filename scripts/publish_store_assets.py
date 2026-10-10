"""Publish the store's files: public previews, and the paid PDFs.

Two jobs, deliberately kept in one script because they must not disagree about
which file belongs to which product.

  previews  Extract the first N pages of each print master into a small PDF and
            upload it to the PUBLIC papers bucket. These are meant to be seen.

  files     Upload the full workbook and mark-scheme volumes to the PRIVATE
            store bucket and register them against the digital variant. These
            must never touch the public bucket: it is served through a
            pub-*.r2.dev domain, which makes every key in it world-readable.

Usage
-----
  python scripts/publish_store_assets.py previews
  python scripts/publish_store_assets.py previews --product mathematics-b-part-1
  python scripts/publish_store_assets.py files --dry-run
  python scripts/publish_store_assets.py files

Reads credentials from .env.local.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import boto3
import fitz
import psycopg2
from botocore.config import Config

ROOT = Path(__file__).resolve().parent.parent
PREVIEW_PAGES = 30
PREVIEW_PREFIX = "store/previews"
FILE_PREFIX = "books"


# ── Product definitions ──────────────────────────────────────────────────────
# The cover is page 1 of each print master, so a preview taken from the front
# shows the cover plus the opening pages of the first chapter, which is exactly
# what a buyer wants to check.
@dataclass
class Volume:
    label: str
    path: Path
    download_name: str


@dataclass
class ProductAssets:
    slug: str
    preview_source: Path | None
    volumes: list[Volume] = field(default_factory=list)


MATHSB = ROOT / "data/workbook/mathsb/print/final"
FPM = ROOT / "data/workbook/fpm/print/final"
ACC = ROOT / "data/workbook/accounting"

PRODUCTS: list[ProductAssets] = [
    ProductAssets(
        slug="mathematics-b-part-1",
        preview_source=MATHSB / "Mathematics_B_Workbook_PRINT_Part1.pdf",
        volumes=[
            Volume("Questions", MATHSB / "Mathematics_B_Workbook_PRINT_Part1.pdf",
                   "GradeMax Mathematics B - Workbook Part 1.pdf"),
            Volume("Mark schemes", MATHSB / "Mathematics_B_MarkSchemes_PRINT_Part1.pdf",
                   "GradeMax Mathematics B - Mark Schemes Part 1.pdf"),
        ],
    ),
    ProductAssets(
        slug="mathematics-b-part-2",
        preview_source=MATHSB / "Mathematics_B_Workbook_PRINT_Part2.pdf",
        volumes=[
            Volume("Questions", MATHSB / "Mathematics_B_Workbook_PRINT_Part2.pdf",
                   "GradeMax Mathematics B - Workbook Part 2.pdf"),
            Volume("Mark schemes", MATHSB / "Mathematics_B_MarkSchemes_PRINT_Part2.pdf",
                   "GradeMax Mathematics B - Mark Schemes Part 2.pdf"),
        ],
    ),
    ProductAssets(
        slug="further-pure-mathematics",
        preview_source=FPM / "Further_Pure_Mathematics_Workbook_PRINT.pdf",
        volumes=[
            Volume("Questions", FPM / "Further_Pure_Mathematics_Workbook_PRINT.pdf",
                   "GradeMax Further Pure Mathematics - Workbook.pdf"),
            Volume("Mark schemes", FPM / "Further_Pure_Mathematics_MarkSchemes_PRINT.pdf",
                   "GradeMax Further Pure Mathematics - Mark Schemes.pdf"),
        ],
    ),
    ProductAssets(
        slug="igcse-accounting-formats",
        preview_source=ACC / "IGCSE_Accounting_Chapterwise_Formats.pdf",
        volumes=[
            Volume("Formats booklet", ACC / "IGCSE_Accounting_Chapterwise_Formats.pdf",
                   "GradeMax IGCSE Accounting - Chapterwise Formats.pdf"),
        ],
    ),
]


# ── Environment ──────────────────────────────────────────────────────────────
def load_env() -> None:
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        sys.exit("No .env.local found")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def r2(bucket_env: str) -> tuple[object, str]:
    bucket = os.environ.get(bucket_env, "")
    if not bucket:
        sys.exit(
            f"{bucket_env} is not set.\n\n"
            "Paid files need a PRIVATE bucket. Create one in the Cloudflare\n"
            "dashboard (R2 > Create bucket, name it grademax-store) and do NOT\n"
            "enable public access or an r2.dev domain on it. Then add to .env.local:\n"
            "  R2_STORE_BUCKET=grademax-store\n"
        )
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ.get("R2_STORE_ACCESS_KEY_ID") or os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ.get("R2_STORE_SECRET_ACCESS_KEY") or os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", region_name="auto"),
    )
    return client, bucket


def db():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")


# ── Previews ─────────────────────────────────────────────────────────────────
def count_blank_pages(doc: "fitz.Document", pages: int) -> int:
    """How many of the first `pages` pages carry no drawable content.

    A PDF can be structurally valid, open without complaint and still render
    completely blank — the Accounting booklet did exactly that, because the
    rebuild script left every content stream empty. Publishing a preview of it
    would have shown buyers thirty blank sheets, so this is checked before
    anything is uploaded rather than trusted.
    """
    blank = 0
    for index in range(min(pages, doc.page_count)):
        page = doc[index]
        try:
            has_content = len(page.read_contents().strip()) > 8
        except Exception:
            has_content = False
        if not has_content and not page.get_text().strip() and not page.get_drawings():
            blank += 1
    return blank


def build_preview(source: Path, pages: int, out: Path) -> int:
    """Copy the first `pages` pages into a new PDF and stamp them as a sample.

    Garbage collection and deflate matter here: an untouched slice of these
    files carries the whole document's font and image tables with it, which
    turns a 12-page preview into tens of megabytes.
    """
    doc = fitz.open(source)
    take = min(pages, doc.page_count)

    blank = count_blank_pages(doc, take)
    if blank > take // 2:
        doc.close()
        raise ValueError(
            f"{blank} of the first {take} pages render blank. "
            "The source PDF is broken - fix it before publishing a preview."
        )

    preview = fitz.open()
    preview.insert_pdf(doc, from_page=0, to_page=take - 1)

    # Skip page 1 — it is the cover, and stamping over it looks broken.
    for index in range(1, preview.page_count):
        page = preview[index]
        rect = page.rect
        page.insert_textbox(
            fitz.Rect(rect.x0, rect.y1 - 34, rect.x1, rect.y1 - 12),
            "Sample pages — the full book is available at grademax.me",
            fontname="helv", fontsize=8,
            color=(0.55, 0.55, 0.55), align=fitz.TEXT_ALIGN_CENTER,
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    preview.save(out, garbage=4, deflate=True)
    preview.close()
    doc.close()
    return take


def cmd_previews(args: argparse.Namespace) -> None:
    client, bucket = r2("R2_BUCKET_NAME")  # the PUBLIC bucket, on purpose
    out_dir = ROOT / "data/store/previews"
    conn = db()

    for product in PRODUCTS:
        if args.product and product.slug != args.product:
            continue
        if not product.preview_source:
            print(f"  --   {product.slug}: no preview by design")
            continue
        if not product.preview_source.exists():
            print(f"  !!   {product.slug}: source missing at {product.preview_source}")
            continue

        out = out_dir / f"{product.slug}-preview.pdf"
        try:
            pages = build_preview(product.preview_source, args.pages, out)
        except ValueError as err:
            print(f"  !!   {product.slug}: {err}")
            continue
        size_mb = out.stat().st_size / (1024 * 1024)
        key = f"{PREVIEW_PREFIX}/{product.slug}-preview.pdf"

        if args.dry_run:
            print(f"  DRY  {product.slug}: {pages} pages, {size_mb:.1f} MB -> {key}")
            continue

        with out.open("rb") as fh:
            client.put_object(Bucket=bucket, Key=key, Body=fh, ContentType="application/pdf")

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE store_products SET preview_r2_key = %s, preview_pages = %s WHERE slug = %s",
                (key, pages, product.slug),
            )
        conn.commit()
        print(f"  OK   {product.slug}: {pages} pages, {size_mb:.1f} MB -> {key}")

    conn.close()


# ── Paid files ───────────────────────────────────────────────────────────────
def cmd_files(args: argparse.Namespace) -> None:
    client, bucket = r2("R2_STORE_BUCKET")  # the PRIVATE bucket
    conn = db()

    for product in PRODUCTS:
        if args.product and product.slug != args.product:
            continue

        with conn.cursor() as cur:
            cur.execute(
                """SELECT v.id FROM store_variants v
                     JOIN store_products p ON p.id = v.product_id
                    WHERE p.slug = %s AND v.kind = 'digital'""",
                (product.slug,),
            )
            row = cur.fetchone()
        if not row:
            print(f"  !!   {product.slug}: no digital variant")
            continue
        variant_id = row[0]

        for order, volume in enumerate(product.volumes, start=1):
            if not volume.path.exists():
                print(f"  !!   {product.slug}: missing {volume.path.name}")
                continue

            size = volume.path.stat().st_size
            doc = fitz.open(volume.path)
            page_count = doc.page_count
            doc.close()

            key = f"{FILE_PREFIX}/{product.slug}/{volume.path.name}"
            mb = size / (1024 * 1024)

            if args.dry_run:
                print(f"  DRY  {product.slug} / {volume.label}: {page_count}pp, {mb:.1f} MB -> {key}")
                continue

            print(f"  ..   uploading {volume.path.name} ({mb:.1f} MB)")
            client.upload_file(str(volume.path), bucket, key,
                               ExtraArgs={"ContentType": "application/pdf"})

            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO store_variant_files
                         (variant_id, label, r2_key, file_name, file_bytes, page_count, sort_order)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (variant_id, r2_key) DO UPDATE SET
                         label = EXCLUDED.label, file_name = EXCLUDED.file_name,
                         file_bytes = EXCLUDED.file_bytes, page_count = EXCLUDED.page_count,
                         sort_order = EXCLUDED.sort_order""",
                    (variant_id, volume.label, key, volume.download_name, size, page_count, order),
                )
            conn.commit()
            print(f"  OK   {product.slug} / {volume.label}: {page_count}pp -> {key}")

    conn.close()


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("previews", help="build and publish public sample PDFs")
    p.add_argument("--pages", type=int, default=PREVIEW_PAGES)
    p.add_argument("--product")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_previews)

    f = sub.add_parser("files", help="upload paid PDFs to the private bucket")
    f.add_argument("--product")
    f.add_argument("--dry-run", action="store_true")
    f.set_defaults(func=cmd_files)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
