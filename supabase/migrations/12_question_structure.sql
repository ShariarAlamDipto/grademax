-- Migration 12: Sub-question structure columns on pages.
--
-- Segmentation now parses each question's part structure
-- (scripts/lib/subquestion_parser.py) into manifest.json. These columns let
-- ingest scripts persist it, unlocking mark-targeted worksheets ("build me a
-- 50-mark worksheet") and per-paper mark breakdowns on SEO pages.
--
-- parts JSON shape (matches structure_to_dict()):
--   [{"label": "a", "marks": 2, "subparts": [{"label": "i", "marks": 1}]}]
--
-- Apply via the Supabase dashboard SQL editor. Idempotent.

ALTER TABLE pages ADD COLUMN IF NOT EXISTS parts JSONB;
ALTER TABLE pages ADD COLUMN IF NOT EXISTS marks INTEGER;

COMMENT ON COLUMN pages.parts IS
  'Sub-question structure: [{label, marks, subparts:[{label, marks}]}]. Parsed by scripts/lib/subquestion_parser.py during segmentation.';
COMMENT ON COLUMN pages.marks IS
  'Total marks for the question, from the "(Total for Question N is X marks)" fence. NULL when the fence was absent.';
