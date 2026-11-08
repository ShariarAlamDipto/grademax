// Pure helpers for adding up question marks. Kept apart from questionMarks.ts
// so client components can import them without bundling the per-question
// marks tables (about 10,000 entries) into the browser.

/** Used only for a question whose printed total could not be read. */
export const FALLBACK_QUESTION_MARKS = 4

interface MarksItem {
  marks?: number | null
}

function isKnownMarks(marks: number | null | undefined): marks is number {
  return typeof marks === 'number' && Number.isFinite(marks) && marks > 0
}

export function totalQuestionMarks(items: readonly MarksItem[]): number {
  return items.reduce(
    (sum, item) => sum + (isKnownMarks(item.marks) ? item.marks : FALLBACK_QUESTION_MARKS),
    0,
  )
}

/** True when every item carries its real printed marks (no estimate in the total). */
export function allQuestionMarksKnown(items: readonly MarksItem[]): boolean {
  return items.every((item) => isKnownMarks(item.marks))
}
