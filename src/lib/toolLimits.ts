// Most questions a normal student may put in one worksheet or test. Admins,
// teachers and students with an active Pro Student Pack have no limit. The API
// routes enforce it (see questionLimit.ts); the UI only mirrors it.
export const MAX_QUESTIONS_PER_PAPER = 30

// How long one Pro Student Pack runs from the moment an admin grants it.
export const PRO_PACK_DAYS = 30

// null means no limit.
export type QuestionLimit = number | null

export interface LimitSubject {
  role?: string | null
  proUntil?: string | null
  superAdmin?: boolean
}

export function isProActive(proUntil: string | null | undefined, now: number = Date.now()): boolean {
  if (!proUntil) return false
  const until = Date.parse(proUntil)
  return !Number.isNaN(until) && until > now
}

export function questionLimitFor(subject: LimitSubject, now: number = Date.now()): QuestionLimit {
  if (subject.superAdmin) return null
  if (subject.role === "admin" || subject.role === "teacher") return null
  if (isProActive(subject.proUntil, now)) return null
  return MAX_QUESTIONS_PER_PAPER
}

export function exceedsLimit(count: number, limit: QuestionLimit): boolean {
  return limit !== null && count > limit
}

export function limitMessage(limit: number): string {
  return `Your account can include up to ${limit} questions per paper. The Pro Student Pack removes this limit — contact us to get it.`
}
