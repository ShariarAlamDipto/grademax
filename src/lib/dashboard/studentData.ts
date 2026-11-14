/**
 * Data access for the student dashboard: subjects, completed papers and
 * leaderboards. One place for every query, so the components never build
 * Supabase calls themselves.
 *
 * Works in the browser with the student's own session; row-level security
 * limits every read and write to that student. Tables added by migration 45
 * may not exist yet: such failures come back as `unavailable`, which the UI
 * shows as "not switched on yet" instead of an error.
 */

import type { SupabaseClient } from "@supabase/supabase-js"
import { toLeaderboardRows, type LeaderboardDbRow, type LeaderboardRow } from "@/lib/rewards/stats"

export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; unavailable: boolean; message: string }

interface DbError { code?: string; message: string }

/** PostgREST / Postgres codes for "this table, column or function does not exist". */
const MISSING_CODES = new Set(["42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"])

function fail<T>(error: DbError): Result<T> {
  return { ok: false, unavailable: MISSING_CODES.has(error.code ?? ""), message: error.message }
}

export interface SubjectOption {
  id: string
  name: string
  code: string | null
  level: string | null
  board: string | null
}

export interface PaperOption {
  id: string
  year: number
  season: string
  paperNumber: string
}

export interface CompletionRecord {
  paperId: string
  subjectId: string
  completedAt: string
  rawScore: number | null
  maxScore: number | null
  percentage: number | null
  timed: boolean
}

export interface CompletionInput {
  userId: string
  paperId: string
  subjectId: string
  rawScore: number | null
  maxScore: number | null
  timed: boolean
}

export interface LeaderboardSettings {
  optIn: boolean
  nickname: string
}

const toNumber = (value: unknown): number | null => (value === null || value === undefined ? null : Number(value))

export async function listAllSubjects(db: SupabaseClient): Promise<Result<SubjectOption[]>> {
  const { data, error } = await db.from("subjects").select("id, name, code, level, board").order("name").limit(1000)
  if (error) return fail(error)
  return { ok: true, data: (data ?? []) as SubjectOption[] }
}

export async function listMySubjectIds(db: SupabaseClient, userId: string): Promise<Result<string[]>> {
  const { data, error } = await db.from("user_subjects").select("subject_id").eq("user_id", userId)
  if (error) return fail(error)
  return { ok: true, data: (data ?? []).map(row => String(row.subject_id)) }
}

export async function addSubject(db: SupabaseClient, userId: string, subjectId: string): Promise<Result<null>> {
  const { error } = await db.from("user_subjects").upsert(
    { user_id: userId, subject_id: subjectId },
    { onConflict: "user_id,subject_id", ignoreDuplicates: true },
  )
  return error ? fail(error) : { ok: true, data: null }
}

export async function removeSubject(db: SupabaseClient, userId: string, subjectId: string): Promise<Result<null>> {
  const { error } = await db.from("user_subjects").delete().eq("user_id", userId).eq("subject_id", subjectId)
  return error ? fail(error) : { ok: true, data: null }
}

/** How many past papers each subject has, for the progress bars. */
export async function countPapers(db: SupabaseClient, subjectIds: readonly string[]): Promise<Record<string, number>> {
  const counts = await Promise.all(subjectIds.map(async id => {
    const { count, error } = await db.from("papers").select("id", { count: "exact", head: true }).eq("subject_id", id)
    if (error) console.error("[dashboard] paper count failed:", error.message)
    return [id, count ?? 0] as const
  }))
  return Object.fromEntries(counts)
}

export async function listPapers(db: SupabaseClient, subjectId: string): Promise<Result<PaperOption[]>> {
  const { data, error } = await db
    .from("papers")
    .select("id, year, season, paper_number")
    .eq("subject_id", subjectId)
    .order("year", { ascending: false })
    .order("season")
    .order("paper_number")
    .limit(1500)
  if (error) return fail(error)
  return {
    ok: true,
    data: (data ?? []).map(row => ({
      id: String(row.id),
      year: Number(row.year),
      season: String(row.season ?? ""),
      paperNumber: String(row.paper_number ?? ""),
    })),
  }
}

export async function listCompletions(db: SupabaseClient, userId: string): Promise<Result<CompletionRecord[]>> {
  const { data, error } = await db
    .from("paper_completions")
    .select("paper_id, subject_id, completed_at, raw_score, max_score, percentage, timed")
    .eq("user_id", userId)
    .limit(3000)
  if (error) return fail(error)
  return {
    ok: true,
    data: (data ?? []).map(row => ({
      paperId: String(row.paper_id),
      subjectId: String(row.subject_id),
      completedAt: String(row.completed_at),
      rawScore: toNumber(row.raw_score),
      maxScore: toNumber(row.max_score),
      percentage: toNumber(row.percentage),
      timed: Boolean(row.timed),
    })),
  }
}

/** Tick a paper as completed, or update its score. The first tick sets the date. */
export async function saveCompletion(db: SupabaseClient, input: CompletionInput): Promise<Result<CompletionRecord>> {
  const { data, error } = await db
    .from("paper_completions")
    .upsert(
      {
        user_id: input.userId,
        paper_id: input.paperId,
        subject_id: input.subjectId,
        raw_score: input.rawScore,
        max_score: input.maxScore,
        timed: input.timed,
      },
      { onConflict: "user_id,paper_id" },
    )
    .select("paper_id, subject_id, completed_at, raw_score, max_score, percentage, timed")
    .single()
  if (error) return fail(error)
  return {
    ok: true,
    data: {
      paperId: String(data.paper_id),
      subjectId: String(data.subject_id),
      completedAt: String(data.completed_at),
      rawScore: toNumber(data.raw_score),
      maxScore: toNumber(data.max_score),
      percentage: toNumber(data.percentage),
      timed: Boolean(data.timed),
    },
  }
}

export async function removeCompletion(db: SupabaseClient, userId: string, paperId: string): Promise<Result<null>> {
  const { error } = await db.from("paper_completions").delete().eq("user_id", userId).eq("paper_id", paperId)
  return error ? fail(error) : { ok: true, data: null }
}

export async function loadLeaderboard(
  db: SupabaseClient,
  subjectId: string | null,
  since: Date | null,
  maxRows = 20,
): Promise<Result<LeaderboardRow[]>> {
  const { data, error } = await db.rpc("subject_leaderboard", {
    p_subject_id: subjectId,
    p_since: since ? since.toISOString() : null,
    p_max_rows: maxRows,
  })
  if (error) return fail(error)
  return { ok: true, data: toLeaderboardRows((data ?? []) as LeaderboardDbRow[]) }
}

export async function getLeaderboardSettings(db: SupabaseClient, userId: string): Promise<Result<LeaderboardSettings>> {
  const { data, error } = await db.from("profiles").select("leaderboard_opt_in, leaderboard_name").eq("id", userId).single()
  if (error) return fail(error)
  return { ok: true, data: { optIn: Boolean(data.leaderboard_opt_in), nickname: String(data.leaderboard_name ?? "") } }
}

export const NICKNAME_MIN = 2
export const NICKNAME_MAX = 24

/** A nickname as it will be stored: trimmed, or null when left empty. */
export function cleanNickname(raw: string): { value: string | null; error: string | null } {
  const value = raw.trim().replace(/\s+/g, " ")
  if (value === "") return { value: null, error: null }
  if (value.length < NICKNAME_MIN || value.length > NICKNAME_MAX) {
    return { value: null, error: `Use ${NICKNAME_MIN}–${NICKNAME_MAX} characters.` }
  }
  if (/[@<>]|https?:/i.test(value)) return { value: null, error: "Leave out email addresses and links." }
  return { value, error: null }
}

export async function saveLeaderboardSettings(
  db: SupabaseClient,
  userId: string,
  settings: LeaderboardSettings,
): Promise<Result<null>> {
  const nickname = cleanNickname(settings.nickname)
  if (nickname.error) return { ok: false, unavailable: false, message: nickname.error }
  const { error } = await db
    .from("profiles")
    .update({ leaderboard_opt_in: settings.optIn, leaderboard_name: nickname.value })
    .eq("id", userId)
  return error ? fail(error) : { ok: true, data: null }
}
