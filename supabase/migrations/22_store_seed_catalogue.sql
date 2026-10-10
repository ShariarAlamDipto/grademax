-- Migration 22: Store — seed the catalogue
-- =============================================================================
-- Four products, each sellable as a printed copy or as a digital download.
-- Page counts and file sizes are transcribed from the delivered PRINT_SPEC.md
-- files, not estimated.
--
-- PRICES
-- ------
--   Mathematics B Part 1 ..... 600 BDT
--   Mathematics B Part 2 ..... 600 BDT
--   Further Pure Mathematics . 800 BDT
--   IGCSE Accounting formats . placeholder, product left INACTIVE until priced
--
-- The digital variant is seeded at the SAME price as the print copy, because
-- that is the figure that was given and inventing a discount would be guessing.
-- Both are editable at /admin/store/products without a migration.
--
-- Products stay `is_active = FALSE` until their PDFs have been uploaded to the
-- private bucket, so the store cannot take money for a file it cannot deliver.
-- Flip them on from the admin portal.
--
-- Idempotent: re-running updates the copy and leaves prices/stock alone.
-- =============================================================================

BEGIN;

INSERT INTO store_products (slug, title, subtitle, subject_code, spec_summary, description, preview_pages, sort_order, is_active)
VALUES
  ('mathematics-b-part-1',
   'Mathematics B — Chapterwise Workbook, Part 1',
   'Edexcel IGCSE 4MB1 · Chapters 1–5',
   '4MB1',
   '469 pages of questions + 633 pages of mark schemes',
   'Every Mathematics B past-paper question from chapters 1 to 5 — Number, Sets, Algebra, Functions and Matrices — regrouped chapter by chapter and section by section, so you practise one skill until it is finished instead of meeting it once per paper. Reproduced at 1:1 from the board''s own sheets, so the ruled answer lines and the original spacing are intact. Supplied with a separate, fully worked mark-scheme volume.',
   12, 1, FALSE),

  ('mathematics-b-part-2',
   'Mathematics B — Chapterwise Workbook, Part 2',
   'Edexcel IGCSE 4MB1 · Chapters 6–11',
   '4MB1',
   '479 pages of questions + 575 pages of mark schemes',
   'The second volume of the Mathematics B chapterwise workbook, covering chapters 6 to 11 — Geometry, Mensuration, Vectors and transformation geometry, and the rest of the specification. A complete book in its own right, with its own contents, summary-and-formulae section and question index. Supplied with a separate mark-scheme volume.',
   12, 2, FALSE),

  ('further-pure-mathematics',
   'Further Pure Mathematics — Chapterwise Workbook',
   'Edexcel IGCSE 4PM1 · Complete specification',
   '4PM1',
   '642 pages of questions + 578 pages of mark schemes',
   'The whole of Further Pure Mathematics, every past-paper question sorted into the specification''s own chapter order — logarithms and indices, the quadratic function, identities and inequalities, graphs, series, the binomial series, vectors, coordinate geometry, calculus and trigonometry. Recurring question shapes are clustered together on purpose: meeting the same archetype four times in four papers'' clothing is how pattern recognition gets built. Supplied with a separate mark-scheme volume.',
   12, 3, FALSE),

  ('igcse-accounting-formats',
   'IGCSE Accounting — Chapterwise Formats Booklet',
   'Edexcel IGCSE Accounting · Every statement format',
   '4AC1',
   '156 pages',
   'Every format an IGCSE Accounting paper can ask you to produce, laid out chapter by chapter — the income statement, the statement of financial position, control accounts, the manufacturing account, incomplete records and the rest. A reference booklet to work alongside, not a question bank.',
   NULL, 4, FALSE)
ON CONFLICT (slug) DO UPDATE SET
  title        = EXCLUDED.title,
  subtitle     = EXCLUDED.subtitle,
  subject_code = EXCLUDED.subject_code,
  spec_summary = EXCLUDED.spec_summary,
  description  = EXCLUDED.description,
  preview_pages= EXCLUDED.preview_pages,
  sort_order   = EXCLUDED.sort_order;

-- ── Variants ─────────────────────────────────────────────────────────────────
-- ON CONFLICT DO NOTHING so a re-run never resets a price or a stock count the
-- owner has since changed in the admin portal.
INSERT INTO store_variants (product_id, kind, label, price_bdt, stock_qty, allow_cod, weight_grams, page_count, is_active)
SELECT p.id, v.kind, v.label, v.price_bdt, v.stock_qty, v.allow_cod, v.weight_grams, v.page_count, TRUE
FROM store_products p
JOIN (VALUES
  ('mathematics-b-part-1',     'print',   'Printed copy — spiral bound, 2 volumes', 600, 0,    TRUE,  3200, 1102),
  ('mathematics-b-part-1',     'digital', 'Digital PDF — instant download',         600, NULL, FALSE, NULL, 1102),
  ('mathematics-b-part-2',     'print',   'Printed copy — spiral bound, 2 volumes', 600, 0,    TRUE,  3100, 1054),
  ('mathematics-b-part-2',     'digital', 'Digital PDF — instant download',         600, NULL, FALSE, NULL, 1054),
  ('further-pure-mathematics', 'print',   'Printed copy — spiral bound, 2 volumes', 800, 0,    TRUE,  3500, 1220),
  ('further-pure-mathematics', 'digital', 'Digital PDF — instant download',         800, NULL, FALSE, NULL, 1220),
  ('igcse-accounting-formats', 'print',   'Printed copy — spiral bound',            0,   0,    TRUE,  450,  156),
  ('igcse-accounting-formats', 'digital', 'Digital PDF — instant download',         0,   NULL, FALSE, NULL, 156)
) AS v(slug, kind, label, price_bdt, stock_qty, allow_cod, weight_grams, page_count)
  ON v.slug = p.slug
ON CONFLICT (product_id, kind) DO NOTHING;

COMMIT;
