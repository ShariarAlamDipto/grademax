# Storage Architecture (post-R2 migration)

As of the R2 migration (Phases A–F, May 2026), every PDF that GradeMax serves
lives in Cloudflare R2. Supabase is used only for Postgres + Auth.

For the pre-migration baseline see [storage-snapshot-pre-r2.md](./storage-snapshot-pre-r2.md).

---

## What lives where

```
┌─────────────────────────┐       ┌──────────────────────────────┐
│ Cloudflare R2           │       │ Postgres (Supabase)           │
│ bucket: grademax-papers │       │ (data + auth only)            │
│                         │       │                              │
│ igcse/...   ──┐         │       │ papers.pdf_url               │
│ ial/...     ──┼─ full   │ ◄──── │ papers.markscheme_pdf_url    │
│ ICT/...     ──┘  papers │       │ papers.data_file_url         │
│                         │       │                              │
│ subjects/X/pages/...    │ ◄──── │ pages.qp_page_url            │
│   per-question PDFs     │       │ pages.ms_page_url            │
│                         │       │ questions.page_pdf_url       │
│                         │       │ questions.ms_pdf_url         │
│                         │       │                              │
│ lectures/<subject>/...  │ ◄──── │ lectures.file_url            │
└─────────────────────────┘       └──────────────────────────────┘
                ▲
                │   (Worksheet Generator + Test Builder
                │   fetch each URL directly from the browser
                │   and merge via pdf-lib in clientPdfBuild.ts)
                │
        ┌───────┴────────┐
        │     browser    │
        └────────────────┘
```

- **R2 keys are stable.** A migration script writes the same key the file had
  in Supabase storage (`subjects/{Subject}/pages/{Year}_{Season}_{N}/q{N}.pdf`),
  so the DB-stored URL is just a host swap.
- **Past papers** are served as plain `<a href={url} target="_blank">` from the
  past-papers viewer ([src/app/past-papers/[subject]/[year]/[season]/[paper]/page.tsx](../src/app/past-papers/[subject]/[year]/[season]/[paper]/page.tsx)).
- **Per-question PDFs** are fetched and merged in the browser by
  [src/lib/clientPdfBuild.ts](../src/lib/clientPdfBuild.ts). That fetch is
  cross-origin to R2 and is governed by the CORS rule documented below.

## CORS rule (Cloudflare dashboard → R2 → grademax-papers → Settings)

```json
[
  {
    "AllowedOrigins": [
      "https://grademax.me",
      "https://www.grademax.me",
      "https://grademax.vercel.app",
      "http://localhost:3000",
      "http://localhost:3001"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["Content-Length", "Content-Range", "Content-Type", "ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Verify:
```
curl -I -H "Origin: https://grademax.me" \
  "https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev/subjects/Biology/pages/2023_May-Jun_2R/q6.pdf"
# Access-Control-Allow-Origin must echo "https://grademax.me"
```

## Writer paths

| Endpoint | Writes to | Notes |
|---|---|---|
| [`POST /api/admin/papers/upload`](../src/app/api/admin/papers/upload/route.ts) | R2 + `papers` row | Full paper PDF upload (admin only) |
| [`POST /api/lectures/upload`](../src/app/api/lectures/upload/route.ts) | R2 + `lectures` row | Teacher upload (post Phase E) |
| `POST /api/worksheets/generate-v2` | DB only (worksheets row) | PDF is built fresh in the browser, never stored |
| Test Builder save | DB only (tests + test_items rows) | Same |
| Python ingest scripts (per-question) | R2 + `pages` rows | `scripts/upload_local_pdfs_to_r2.py` and friends |

There are no longer any code paths that write to Supabase Storage.

## URL-leak guard

[`scripts/check_no_supabase_urls.py`](../scripts/check_no_supabase_urls.py)
fails non-zero if any DB URL column points back at Supabase Storage.
Runs daily and on every PR via
[`.github/workflows/storage-leak-check.yml`](../.github/workflows/storage-leak-check.yml).

## Admin overview banner

The `/admin` page renders an amber/red banner if Supabase Storage usage
exceeds 25 %/80 % of the 1 GB free-tier limit. Source: the new
`supabaseStorageBytes` field on [`/api/admin/stats`](../src/app/api/admin/stats/route.ts).

After Phase D (delete `question-pdfs` bucket), the expected steady-state
banner threshold is < 12 MB (lectures bucket, if Phase E hasn't fully purged
the empty bucket).

## Phase D — completed

Supabase Storage buckets `question-pdfs` and `lectures` were emptied
in two passes (the initial `.list()` walker undercounted because some
folders exceeded the 1000-entry page limit; a second pass swept up the
remaining 3 630 files).

| Bucket | Files before | Files after | Bytes after |
|---|---:|---:|---:|
| `question-pdfs` | 18 487 | 0 | 0 |
| `lectures` | 10 | 0 | 0 |

Supabase Storage usage: **0 MB.** Free tier limit (1 GB) no longer at risk.

Phase D pre-flight verified all 13 806 DB-referenced R2 URLs (`pages` +
`questions` + `papers` + `lectures`) resolve before delete; see
[scripts/phase_d_verify_r2_coverage.py](../scripts/phase_d_verify_r2_coverage.py).

## Known data hygiene items (open)

- **Migration 10 (`supabase/migrations/10_phase_f_cleanup.sql`)**: schema
  changes (drop legacy `papers` columns `qp_source_path` / `ms_source_path`
  / `total_pages`, add `data_file_url` if missing, add `usage_events`
  btree index, add column comments). Apply via Supabase dashboard SQL
  Editor when convenient. The live DB already has the core shape; the
  migration is mostly idempotent documentation.
- **`pages` + `questions` duality — RESOLVED.** Migration 11
  (`supabase/migrations/11_drop_questions_duality.sql`) drops `questions`,
  `question_tags`, and `question_topics`; `pages` is the single canonical
  table. `worksheet_items.question_id` now references `pages(id)` directly
  (the UUIDs were already shared). Apply migration 11 via the dashboard SQL
  editor if it hasn't been run yet.
- **137 zombie URLs** flagged in Phase B (see
  [phaseB-zombie-urls.txt](./phaseB-zombie-urls.txt)) have been NULL-ed in
  both `pages` and `questions` tables. The underlying paper folders
  (`Further_Pure_Mathematics/pages/2017_Nov_*P/` etc.) reference papers
  whose source PDFs never existed in Supabase Storage. Re-segmenting and
  uploading those nine FPM papers is a content task, not a storage one.
