// Per-subject filter behaviour for the worksheet generator and test builder.
// The subject list itself lives in TOOL_SUBJECT_SLOTS (toolSubjects.ts).

// No tool subject is tagged by whole exam paper any more. Accounting has been
// chapterwise since 2026-10-16 (scripts/apply_accounting_tool_topics.py), and
// Business and Economics since 2026-11-07 (scripts/chapterwise_igcse_business.py,
// scripts/chapterwise_igcse_economics.py). Kept so a future subject can be
// published by paper first.
const EXAM_PAPER_FILTER_CODES: readonly string[] = []

// Whole questions grouped by specification chapter; one question may cover several.
// IAL Accounting (WAC) is chapterwise from its first publish (scripts/onboard_ial_accounting.py).
const CHAPTER_FILTER_CODES: readonly string[] = ['4CP1', '4CP0', '4BS1', '4BS0', '4EC1', '4EC0', 'WAC']

export function usesExamPaperFilters(code: string): boolean {
  return EXAM_PAPER_FILTER_CODES.includes(code)
}

export function usesChapterFilters(code: string): boolean {
  return CHAPTER_FILTER_CODES.includes(code)
}

// The archive's original 4CP1 ID holds Pearson's 4CP0 specification papers.
export function toolSubjectDisplayCode(code: string): string {
  return code === '4CP1' ? '4CP0' : code
}
