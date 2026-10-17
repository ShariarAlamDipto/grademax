import commerceMarks from './commerceQuestionMarks.json'
import computerScienceMarks from './computerScienceQuestionMarks.json'

const knownMarks: Record<string, number> = { ...commerceMarks, ...computerScienceMarks }

export function getQuestionMarks(paperId: string, questionNumber: string): number | null {
  return knownMarks[`${paperId}|${questionNumber}`] ?? null
}

// Older question banks do not provide marks; keep their existing estimate.
export function totalQuestionMarks(items: readonly { marks?: number | null }[]): number {
  return items.reduce((sum, item) => sum + (
    typeof item.marks === 'number' && Number.isFinite(item.marks) && item.marks > 0 ? item.marks : 4
  ), 0)
}
