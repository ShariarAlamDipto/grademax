// Per-subject filter behaviour for the worksheet generator and test builder.
// The subject list itself lives in TOOL_SUBJECT_SLOTS (toolSubjects.ts).

// Business and Economics are still tagged by whole exam paper. Accounting is
// chapterwise (4AC1 specification sections, with difficulty) since 2026-10-16:
// scripts/apply_accounting_tool_topics.py.
export function usesExamPaperFilters(code: string): boolean {
  return ['4BS1', '4BS0', '4EC1', '4EC0'].includes(code)
}

export function usesChapterFilters(code: string): boolean {
  return ['4CP1', '4CP0'].includes(code)
}

// The archive's original 4CP1 ID holds Pearson's 4CP0 specification papers.
export function toolSubjectDisplayCode(code: string): string {
  return code === '4CP1' ? '4CP0' : code
}
