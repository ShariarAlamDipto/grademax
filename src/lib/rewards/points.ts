/**
 * Progression points and the facts the badges are judged on, worked out from a
 * student's completed papers. Pure functions: no database access.
 */

export const POINTS = {
  /** Finishing a paper at all. */
  completed: 20,
  /** Extra points per percentage point scored (so 100% adds 30). */
  perPercent: 0.3,
  /** Sitting the paper under exam conditions. */
  timed: 5,
} as const

export interface Completion {
  subjectId: string
  /** ISO timestamp. */
  completedAt: string
  /** 0–100, or null when the student ticked the box without a score. */
  percentage: number | null
  timed: boolean
}

/**
 * Points for one completed paper: 20, plus up to 30 for the score, plus 5 if
 * timed. MUST match completion_points() in migration 45, which ranks the
 * leaderboards.
 */
export function completionPoints(percentage: number | null, timed: boolean): number {
  const score = percentage === null ? 0 : Math.round(Math.min(Math.max(percentage, 0), 100) * POINTS.perPercent)
  return POINTS.completed + score + (timed ? POINTS.timed : 0)
}

/** Percentage from a raw score, or null when either number is missing or invalid. */
export function percentageOf(rawScore: number | null, maxScore: number | null): number | null {
  if (rawScore === null || maxScore === null) return null
  if (!Number.isFinite(rawScore) || !Number.isFinite(maxScore) || maxScore <= 0 || rawScore < 0) return null
  return Math.round(Math.min(rawScore / maxScore, 1) * 1000) / 10
}

/** The UTC calendar day of a timestamp, as days since the epoch. */
function dayNumber(iso: string): number {
  return Math.floor(new Date(iso).getTime() / 86_400_000)
}

/** Longest run of consecutive calendar days (UTC) with at least one completion. */
export function longestStreakDays(completedAt: readonly string[]): number {
  const days = [...new Set(completedAt.map(dayNumber).filter(Number.isFinite))].sort((a, b) => a - b)
  let longest = 0
  let run = 0
  days.forEach((day, i) => {
    run = i > 0 && day === days[i - 1] + 1 ? run + 1 : 1
    longest = Math.max(longest, run)
  })
  return longest
}

export interface CompletionSummary {
  papersCompleted: number
  /** Progression points from every completed paper. */
  paperPoints: number
  bestPercentage: number | null
  averagePercentage: number | null
  timedPapers: number
  /** Most papers completed in any single subject. */
  mostPapersInOneSubject: number
  longestStreakDays: number
  /** Points and paper count per subject id. */
  bySubject: Record<string, { papers: number; points: number }>
}

export function summariseCompletions(rows: readonly Completion[]): CompletionSummary {
  const scores = rows.map(r => r.percentage).filter((p): p is number => p !== null && Number.isFinite(p))
  const bySubject = rows.reduce<Record<string, { papers: number; points: number }>>((acc, row) => {
    const current = acc[row.subjectId] ?? { papers: 0, points: 0 }
    return {
      ...acc,
      [row.subjectId]: {
        papers: current.papers + 1,
        points: current.points + completionPoints(row.percentage, row.timed),
      },
    }
  }, {})
  const subjectTotals = Object.values(bySubject)

  return {
    papersCompleted: rows.length,
    paperPoints: subjectTotals.reduce((sum, s) => sum + s.points, 0),
    bestPercentage: scores.length > 0 ? Math.max(...scores) : null,
    averagePercentage: scores.length > 0
      ? Math.round((scores.reduce((sum, p) => sum + p, 0) / scores.length) * 10) / 10
      : null,
    timedPapers: rows.filter(r => r.timed).length,
    mostPapersInOneSubject: subjectTotals.reduce((most, s) => Math.max(most, s.papers), 0),
    longestStreakDays: longestStreakDays(rows.map(r => r.completedAt)),
    bySubject,
  }
}

/** Monday 00:00 UTC of the week containing `date`: the weekly leaderboard's start. */
export function weekStartUtc(date: Date): Date {
  const daysSinceMonday = (date.getUTCDay() + 6) % 7
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() - daysSinceMonday))
}
