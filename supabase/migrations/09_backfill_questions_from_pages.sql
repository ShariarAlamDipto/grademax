-- Migration 09: Backfill questions + question_tags from the existing pages table
--
-- The worksheet generator queries `questions` + `question_tags`, but the live
-- dataset (4 932 rows) was ingested into `pages` by the page_based scripts.
-- This migration projects each questionable page into a `questions` row and
-- unrolls its `topics[]` array into `question_tags` rows.
--
-- Mapping (per page where is_question = TRUE and qp_page_url IS NOT NULL):
--   pages.id              → questions.id              (same UUID — idempotent)
--   pages.paper_id        → questions.paper_id
--   pages.question_number → questions.question_number
--   pages.difficulty      → questions.difficulty
--   pages.qp_page_url     → questions.page_pdf_url
--   pages.ms_page_url     → questions.ms_pdf_url
--   pages.has_diagram     → questions.has_diagram
--   pages.text_excerpt    → questions.text_excerpt
--   pages.created_at      → questions.created_at
--   each topic in pages.topics[] → one question_tags row (question_id, topic)
--
-- Re-runnable: ON CONFLICT DO NOTHING on both inserts.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Project pages → questions
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO questions (
  id, paper_id, question_number, difficulty,
  page_pdf_url, ms_pdf_url, has_diagram, text_excerpt, created_at
)
SELECT
  p.id,
  p.paper_id,
  p.question_number,
  p.difficulty,
  p.qp_page_url,
  p.ms_page_url,
  COALESCE(p.has_diagram, FALSE),
  p.text_excerpt,
  COALESCE(p.created_at, NOW())
FROM pages p
WHERE p.is_question = TRUE
  AND p.qp_page_url IS NOT NULL
ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Unroll pages.topics[] → question_tags
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO question_tags (question_id, topic)
SELECT
  p.id,
  t AS topic
FROM pages p
CROSS JOIN LATERAL UNNEST(p.topics) AS t
WHERE p.is_question = TRUE
  AND p.qp_page_url IS NOT NULL
  AND t IS NOT NULL
  AND t <> ''
ON CONFLICT (question_id, topic) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Summary
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  src_count          INT;
  src_with_url_count INT;
  q_count            INT;
  qt_count           INT;
  q_with_tags_count  INT;
BEGIN
  SELECT COUNT(*) INTO src_count          FROM pages WHERE is_question = TRUE;
  SELECT COUNT(*) INTO src_with_url_count FROM pages WHERE is_question = TRUE AND qp_page_url IS NOT NULL;
  SELECT COUNT(*) INTO q_count            FROM questions;
  SELECT COUNT(*) INTO qt_count           FROM question_tags;
  SELECT COUNT(DISTINCT question_id) INTO q_with_tags_count FROM question_tags;

  RAISE NOTICE '--- Migration 09 complete ---';
  RAISE NOTICE '  source pages (is_question = true):                  %', src_count;
  RAISE NOTICE '  source pages with qp_page_url:                      %', src_with_url_count;
  RAISE NOTICE '  questions table now has:                            % rows', q_count;
  RAISE NOTICE '  question_tags table now has:                        % rows', qt_count;
  RAISE NOTICE '  questions covered by at least one tag:              %', q_with_tags_count;
END $$;

COMMIT;
