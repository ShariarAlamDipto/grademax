/**
 * Loads one student's activity for the rewards panel.
 *
 * Reads through the student's own session, so row-level security keeps every
 * count to that student. worksheets, worksheet_items, tests and user_subjects
 * exist today; paper_completions, question_solves, community_contributions and
 * the leaderboard function arrive with migration 45. Until it is applied those
 * lookups fail and are reported as "not available" (null / false), never as a
 * misleading zero.
 */

import type { SupabaseClient } from "@supabase/supabase-js"
import type { RewardStats } from "./badges"
import { summariseCompletions, weekStartUtc, type Completion } from "./points"

export interface RecentResult {
  label: string
  percentage: number
}

export interface LeaderboardRow {
  rank: number
  displayName: string
  papers: number
  points: number
  averagePercentage: number | null
  isMe: boolean
}

export interface RewardsData {
  stats: RewardStats
  /** false until migration 45 is applied: completed papers cannot be saved yet. */
  progressAvailable: boolean
  /** The student's latest scored papers, oldest first, for the chart. */
  recent: RecentResult[]
  /** This week's all-subject leaderboard, or null while it is not switched on. */
  weekly: LeaderboardRow[] | null
}

const RECENT_RESULTS = 8
const WEEKLY_ROWS = 10

interface CountResult { count: number | null; error: { message: string } | null }

/** A count that failed is logged and treated as nothing recorded. */
function countOrZero(label: string, result: CountResult): number {
  if (result.error) {
    console.error(`[rewards] ${label} count failed:`, result.error.message)
    return 0
  }
  return result.count ?? 0
}

/** A count from a table that may not exist yet: null means "not switched on". */
function countOrNull(result: CountResult): number | null {
  return result.error ? null : result.count ?? 0
}

interface TestRow { total_questions: number | null }
interface PaperRef { year: number | null; season: string | null; paper_number: string | null }
interface CompletionDbRow {
  subject_id: string
  completed_at: string
  percentage: number | null
  timed: boolean
  papers: PaperRef | PaperRef[] | null
}
export interface LeaderboardDbRow {
  rank: number
  display_name: string
  papers: number
  points: number
  average_percentage: number | null
  is_me: boolean
}

export function toLeaderboardRows(rows: readonly LeaderboardDbRow[]): LeaderboardRow[] {
  return rows.map(row => ({
    rank: Number(row.rank),
    displayName: row.display_name,
    papers: Number(row.papers),
    points: Number(row.points),
    averagePercentage: row.average_percentage === null ? null : Math.round(Number(row.average_percentage)),
    isMe: row.is_me,
  }))
}

function paperLabel(ref: PaperRef | PaperRef[] | null): string {
  const paper = Array.isArray(ref) ? ref[0] : ref
  if (!paper) return "Paper"
  return [paper.paper_number ? `P${paper.paper_number}` : null, paper.season, paper.year].filter(Boolean).join(" ") || "Paper"
}

export async function loadRewards(db: SupabaseClient, userId: string): Promise<RewardsData> {
  const [worksheets, worksheetItems, tests, subjects, completions, solves, contributions, weekly] = await Promise.all([
    db.from("worksheets").select("id", { count: "exact", head: true }).eq("user_id", userId),
    db.from("worksheet_items").select("worksheet_id, worksheets!inner(user_id)", { count: "exact", head: true }).eq("worksheets.user_id", userId),
    db.from("tests").select("total_questions").eq("user_id", userId).limit(2000),
    db.from("user_subjects").select("subject_id", { count: "exact", head: true }).eq("user_id", userId),
    db.from("paper_completions")
      .select("subject_id, completed_at, percentage, timed, papers(year, season, paper_number)")
      .eq("user_id", userId)
      .order("completed_at", { ascending: true })
      .limit(3000),
    db.from("question_solves").select("question_id", { count: "exact", head: true }).eq("user_id", userId),
    db.from("community_contributions").select("id", { count: "exact", head: true }).eq("user_id", userId).eq("status", "accepted"),
    db.rpc("subject_leaderboard", { p_subject_id: null, p_since: weekStartUtc(new Date()).toISOString(), p_max_rows: WEEKLY_ROWS }),
  ])

  if (tests.error) console.error("[rewards] tests lookup failed:", tests.error.message)
  const testRows = (tests.data ?? []) as TestRow[]
  const testQuestions = testRows.reduce((sum, t) => sum + (t.total_questions ?? 0), 0)

  const completionRows = (completions.data ?? []) as unknown as CompletionDbRow[]
  const summary = summariseCompletions(completionRows.map((row): Completion => ({
    subjectId: row.subject_id,
    completedAt: row.completed_at,
    percentage: row.percentage === null ? null : Number(row.percentage),
    timed: row.timed,
  })))
  const scored = completionRows.filter(row => row.percentage !== null)

  const stats: RewardStats = {
    questionsGenerated: countOrZero("worksheet_items", worksheetItems) + testQuestions,
    worksheetsMade: countOrZero("worksheets", worksheets),
    testsBuilt: testRows.length,
    papersLogged: summary.papersCompleted,
    paperPoints: summary.paperPoints,
    papersScored: scored.length,
    bestPercentage: summary.bestPercentage,
    averagePercentage: summary.averagePercentage,
    timedPapers: summary.timedPapers,
    mostPapersInOneSubject: summary.mostPapersInOneSubject,
    longestStreakDays: summary.longestStreakDays,
    subjectsEnrolled: countOrZero("user_subjects", subjects),
    questionsSolved: countOrNull(solves),
    contributions: countOrNull(contributions),
  }

  return {
    stats,
    progressAvailable: !completions.error,
    recent: scored.slice(-RECENT_RESULTS).map(row => ({
      label: paperLabel(row.papers),
      percentage: Math.round(Number(row.percentage)),
    })),
    weekly: weekly.error ? null : toLeaderboardRows((weekly.data ?? []) as LeaderboardDbRow[]),
  }
}
