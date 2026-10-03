-- Migration 31: Store — sell Mathematics B as one two-volume set
-- =============================================================================
-- Parts 1 and 2 of the Mathematics B workbook were separate products at
-- 600 BDT each. They are now sold only together, as one product at
-- 600 + 600 = 1200 BDT. Further Pure Mathematics stays its own product.
--
-- The two part products are DEACTIVATED, not deleted: store_order_items points
-- at their variants, and those orders must keep resolving. Their old URLs are
-- redirected to the new product in next.config.
--
-- The new product starts INACTIVE; scripts/publish_store_products.py uploads
-- its cover and preview, sets the measured page count and stock, and switches
-- it on.
--
-- Idempotent: re-running updates the copy and leaves price/stock alone.
-- =============================================================================

BEGIN;

INSERT INTO store_products (slug, title, subtitle, subject_code, spec_summary, description, preview_pages, sort_order, is_active)
VALUES
  ('mathematics-b',
   'Mathematics B — Chapterwise Workbook (Parts 1 & 2)',
   'Edexcel IGCSE 4MB1 · Complete specification · 2 volumes',
   '4MB1',
   '948 pages of questions in 2 volumes',
   'The complete Mathematics B chapterwise workbook, both volumes together. Part 1 covers chapters 1 to 5 — Number, Sets, Algebra, Functions and Matrices; Part 2 covers chapters 6 to 11 — Geometry, Mensuration, Vectors and transformation geometry, and the rest of the specification. Every past-paper question is regrouped chapter by chapter and section by section, so you practise one skill until it is finished instead of meeting it once per paper. Reproduced at 1:1 from the board''s own sheets, so the ruled answer lines and the original spacing are intact.',
   30, 1, FALSE)
ON CONFLICT (slug) DO UPDATE SET
  title        = EXCLUDED.title,
  subtitle     = EXCLUDED.subtitle,
  subject_code = EXCLUDED.subject_code,
  description  = EXCLUDED.description,
  sort_order   = EXCLUDED.sort_order;

INSERT INTO store_variants (product_id, kind, label, price_bdt, stock_qty, allow_cod, weight_grams, page_count, is_active)
SELECT p.id, v.kind, v.label, v.price_bdt, v.stock_qty, v.allow_cod, v.weight_grams, v.page_count, v.is_active
FROM store_products p
JOIN (VALUES
  ('print',   'Printed copy — spiral bound, 2 volumes', 1200, 0,    TRUE,  6300, 948,  TRUE),
  ('digital', 'Digital PDF — instant download',         1200, NULL, FALSE, NULL, 948,  FALSE)
) AS v(kind, label, price_bdt, stock_qty, allow_cod, weight_grams, page_count, is_active)
  ON p.slug = 'mathematics-b'
ON CONFLICT (product_id, kind) DO NOTHING;

-- The parts are no longer sold on their own.
UPDATE store_products
   SET is_active = FALSE, updated_at = NOW()
 WHERE slug IN ('mathematics-b-part-1', 'mathematics-b-part-2');

-- Further Pure Mathematics moves up to sit directly after the set.
UPDATE store_products SET sort_order = 2 WHERE slug = 'further-pure-mathematics';

COMMIT;
