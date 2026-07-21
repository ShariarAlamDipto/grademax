// DB-backed catalog helpers for the public MCP connector (/api/mcp).
//
// Unlike catalog.ts (which reads the static build-time papers index), these
// tools read live Supabase tables — but only through the ANON key, and only
// tables that are already public on the site (proven by /api/subjects and
// /api/topics, which use the same key). No service-role client, no cookies.
//
// Question-level data lives in the `pages` table (is_question = true), keyed to
// `papers` by paper_id. Only seven subjects are classified with topics; the rest
// are download-only. CLASSIFIED_SUBJECT_SLUGS lets the tools tell the user when
// a subject simply has no question-level data rather than failing opaquely.

import { createClient, type SupabaseClient } from "@supabase/supabase-js"
import { subjects, dbNameOf, type Subject } from "@/lib/subjects"
import { normalizeTopicCodes } from "@/lib/topicCodes"
import { toAbsolutePdfUrl } from "@/lib/pdfUtils"
import { buildViewerHref, isAllowedPdfUrl } from "@/lib/viewer-link"
import { SITE_ORIGIN } from "@/lib/mcp/catalog"

/**
 * Subjects with question-level topic classification (the test-builder set).
 * Everything else has papers but no ingested/classified questions — see the
 * classification-state notes. Keep in sync with TEST_BUILDER_SUBJECT_SLOTS.
 */
export const CLASSIFIED_SUBJECT_SLUGS = new Set([
  "physics",
  "maths-b",
  "chemistry",
  "biology",
  "human-biology",
  "further-pure-maths",
  "mechanics-1",
])

export const DIFFICULTIES = ["easy", "medium", "hard"] as const
export type Difficulty = (typeof DIFFICULTIES)[number]

export interface TopicSummary {
  code: string
  name: string
  description: string | null
}

export interface QuestionResult {
  id: string
  questionNumber: string
  /** Raw topic ids as stored in pages.topics (kept for reference/filtering). */
  topics: string[]
  /** Human-readable topic names resolved from the topics table. */
  topicNames: string[]
  difficulty: string
  year: number | null
  season: string | null
  paper: string | null
  hasDiagram: boolean
  /**
   * Extracted question text when the subject was ingested with text (Chemistry,
   * Biology, Human Biology, Further Pure Maths, Maths B). `null` for image-only
   * subjects (Physics, Mechanics 1) that have no text in the database.
   */
  questionText: string | null
  /** False when the question is image-only — the PDF is the sole source. */
  textAvailable: boolean
  questionPdfUrl: string | null
  markSchemePdfUrl: string | null
  viewerUrl: string | null
}

let cachedClient: SupabaseClient | null = null

/** Plain anon client — no cookies, no session, read-only public tables. */
function anon(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !key) return null
  if (!cachedClient) {
    cachedClient = createClient(url, key, {
      auth: { autoRefreshToken: false, persistSession: false },
    })
  }
  return cachedClient
}

function findStaticSubject(slugOrName: string): Subject | undefined {
  const needle = slugOrName.trim().toLowerCase()
  return subjects.find(
    (s) => s.slug.toLowerCase() === needle || s.name.toLowerCase() === needle
  )
}

/** Resolve an MCP subject slug to its Supabase subjects.id (UUID). */
async function resolveSubjectId(
  sb: SupabaseClient,
  slug: string
): Promise<{ subject: Subject; id: string } | { error: string }> {
  const subject = findStaticSubject(slug)
  if (!subject) {
    return {
      error: `Unknown subject "${slug}". Use list_subjects to see valid slugs.`,
    }
  }
  const { data, error } = await sb
    .from("subjects")
    .select("id,name")
    .eq("name", dbNameOf(subject))
    .limit(1)
    .maybeSingle()
  if (error) return { error: `Database error resolving subject: ${error.message}` }
  if (!data) {
    return { error: `Subject "${slug}" is not present in the database.` }
  }
  return { subject, id: data.id as string }
}

export async function listTopics(
  slug: string
): Promise<
  | { ok: true; subject: string; classified: boolean; topics: TopicSummary[] }
  | { ok: false; error: string }
> {
  const sb = anon()
  if (!sb) return { ok: false, error: "Server is not configured for database access." }

  const resolved = await resolveSubjectId(sb, slug)
  if ("error" in resolved) return { ok: false, error: resolved.error }

  const { data, error } = await sb
    .from("topics")
    .select("code,name,description")
    .eq("subject_id", resolved.id)
    .order("code")
  if (error) return { ok: false, error: `Failed to fetch topics: ${error.message}` }

  return {
    ok: true,
    subject: resolved.subject.name,
    classified: CLASSIFIED_SUBJECT_SLUGS.has(resolved.subject.slug),
    topics: (data ?? []).map((t) => ({
      code: t.code as string,
      name: t.name as string,
      description: (t.description as string | null) ?? null,
    })),
  }
}

interface PageRow {
  id: string
  paper_id?: string
  page_number: number
  question_number: string | null
  topics: string[] | null
  difficulty: string | null
  qp_page_url: string | null
  ms_page_url: string | null
  has_diagram: boolean | null
  text_excerpt: string | null
  papers: { year: number; season: string; paper_number: string } | null
}

/** Columns fetched for every question row (shared by search + practice test). */
const PAGE_SELECT =
  "id,paper_id,page_number,question_number,topics,difficulty,qp_page_url,ms_page_url,has_diagram,text_excerpt,papers(year,season,paper_number)"

/**
 * Build a map from the topic ids stored in pages.topics to human-readable
 * topic names. pages.topics stores normalized ids (e.g. "3", "M1.1", "1.2"),
 * while the topics table stores codes (e.g. "WAVE", "M1.1", "1.2"); running
 * each code through normalizeTopicCodes yields the same id the pages use, so
 * we can resolve "3" -> "Waves" for the client.
 */
async function loadTopicIdToName(
  sb: SupabaseClient,
  subjectId: string
): Promise<Map<string, string>> {
  const { data } = await sb
    .from("topics")
    .select("code,name")
    .eq("subject_id", subjectId)
  const map = new Map<string, string>()
  for (const t of data ?? []) {
    const code = t.code as string
    const name = t.name as string
    map.set(code, name)
    for (const id of normalizeTopicCodes([code])) map.set(id, name)
  }
  return map
}

function normalizeDifficulty(raw: string | null): string {
  if (!raw || raw === "None") return "unspecified"
  return raw
}

/** Map a `pages` row to the public QuestionResult shape (URLs + viewer link). */
function mapPageRow(
  subjectName: string,
  idToName: Map<string, string>,
  p: PageRow
): QuestionResult {
  const qp = toAbsolutePdfUrl(p.qp_page_url)
  const ms = toAbsolutePdfUrl(p.ms_page_url)
  const viewerHref =
    isAllowedPdfUrl(qp) || isAllowedPdfUrl(ms)
      ? buildViewerHref({
          doc: isAllowedPdfUrl(qp) ? "qp" : "ms",
          qpUrl: qp,
          msUrl: ms,
          title: `${subjectName} ${p.papers?.year ?? ""} ${p.papers?.season ?? ""} Q${p.question_number ?? p.page_number}`.trim(),
          backPath: "/test-builder",
        })
      : null
  const ids = p.topics ?? []
  const rawText = (p.text_excerpt ?? "").trim()
  const textAvailable = rawText.length > 20
  return {
    id: p.id,
    questionNumber: p.question_number || String(p.page_number),
    topics: ids,
    topicNames: ids.map((id) => idToName.get(id) ?? id),
    difficulty: normalizeDifficulty(p.difficulty),
    year: p.papers?.year ?? null,
    season: p.papers?.season ?? null,
    paper: p.papers?.paper_number ?? null,
    hasDiagram: p.has_diagram ?? false,
    questionText: textAvailable ? rawText : null,
    textAvailable,
    questionPdfUrl: qp,
    markSchemePdfUrl: ms,
    viewerUrl: viewerHref ? `${SITE_ORIGIN}${viewerHref}` : null,
  }
}

export async function searchQuestions(opts: {
  subject: string
  topics?: string[]
  difficulty?: Difficulty
  yearStart?: number
  yearEnd?: number
  page?: number
  limit?: number
}): Promise<
  | {
      ok: true
      subject: string
      classified: boolean
      total: number
      page: number
      totalPages: number
      questions: QuestionResult[]
    }
  | { ok: false; error: string }
> {
  const sb = anon()
  if (!sb) return { ok: false, error: "Server is not configured for database access." }

  const resolved = await resolveSubjectId(sb, opts.subject)
  if ("error" in resolved) return { ok: false, error: resolved.error }

  const classified = CLASSIFIED_SUBJECT_SLUGS.has(resolved.subject.slug)
  const page = Math.max(1, opts.page ?? 1)
  const limit = Math.min(50, Math.max(1, opts.limit ?? 20))

  // Step 1: paper IDs for this subject (with optional year window).
  let paperQuery = sb.from("papers").select("id").eq("subject_id", resolved.id)
  if (opts.yearStart) paperQuery = paperQuery.gte("year", opts.yearStart)
  if (opts.yearEnd) paperQuery = paperQuery.lte("year", opts.yearEnd)
  const { data: papers, error: paperErr } = await paperQuery
  if (paperErr) return { ok: false, error: `Failed to fetch papers: ${paperErr.message}` }

  if (!papers || papers.length === 0) {
    return {
      ok: true,
      subject: resolved.subject.name,
      classified,
      total: 0,
      page,
      totalPages: 0,
      questions: [],
    }
  }
  const paperIds = papers.map((p) => p.id as string)

  const topicCodes =
    opts.topics && opts.topics.length > 0
      ? normalizeTopicCodes(opts.topics.map((t) => t.trim()).filter(Boolean))
      : []
  const offset = (page - 1) * limit

  // Step 2: page rows + exact count in one round-trip.
  let q = sb
    .from("pages")
    .select(PAGE_SELECT, { count: "exact" })
    .eq("is_question", true)
    .not("qp_page_url", "is", null)
    .in("paper_id", paperIds)
    .order("page_number", { ascending: true })
    .range(offset, offset + limit - 1)
  if (topicCodes.length > 0) q = q.overlaps("topics", topicCodes)
  if (opts.difficulty) q = q.eq("difficulty", opts.difficulty)

  const { data: pages, count, error: pagesErr } = await q
  if (pagesErr) return { ok: false, error: `Failed to fetch questions: ${pagesErr.message}` }

  const total = count ?? 0
  const rows = (pages ?? []) as unknown as PageRow[]
  const idToName = await loadTopicIdToName(sb, resolved.id)
  const questions = rows.map((p) => mapPageRow(resolved.subject.name, idToName, p))

  return {
    ok: true,
    subject: resolved.subject.name,
    classified,
    total,
    page,
    totalPages: Math.ceil(total / limit),
    questions,
  }
}

/**
 * Round-robin pick across buckets: takes one item from each bucket in turn
 * until `count` is reached or all buckets are exhausted. Gives an even spread
 * across topics (or papers) rather than a run from a single source.
 */
function roundRobin<T>(buckets: T[][], count: number): T[] {
  const out: T[] = []
  let progressed = true
  for (let i = 0; out.length < count && progressed; i++) {
    progressed = false
    for (const bucket of buckets) {
      if (i < bucket.length) {
        out.push(bucket[i]!)
        progressed = true
        if (out.length >= count) break
      }
    }
  }
  return out
}

export interface PracticeTest {
  subject: string
  classified: boolean
  requestedCount: number
  selectedCount: number
  topicBreakdown: Record<string, number>
  difficultyBreakdown: Record<string, number>
  yearsCovered: number[]
  testBuilderUrl: string
  questions: QuestionResult[]
}

export async function buildPracticeTest(opts: {
  subject: string
  topics?: string[]
  difficulty?: Difficulty
  yearStart?: number
  yearEnd?: number
  count?: number
}): Promise<{ ok: true; test: PracticeTest } | { ok: false; error: string }> {
  const sb = anon()
  if (!sb) return { ok: false, error: "Server is not configured for database access." }

  const resolved = await resolveSubjectId(sb, opts.subject)
  if ("error" in resolved) return { ok: false, error: resolved.error }

  const classified = CLASSIFIED_SUBJECT_SLUGS.has(resolved.subject.slug)
  const requestedCount = Math.min(30, Math.max(1, opts.count ?? 10))

  const emptyTest = (): PracticeTest => ({
    subject: resolved.subject.name,
    classified,
    requestedCount,
    selectedCount: 0,
    topicBreakdown: {},
    difficultyBreakdown: {},
    yearsCovered: [],
    testBuilderUrl: `${SITE_ORIGIN}/test-builder`,
    questions: [],
  })

  if (!classified) return { ok: true, test: emptyTest() }

  // Paper IDs for this subject (optional year window).
  let paperQuery = sb.from("papers").select("id").eq("subject_id", resolved.id)
  if (opts.yearStart) paperQuery = paperQuery.gte("year", opts.yearStart)
  if (opts.yearEnd) paperQuery = paperQuery.lte("year", opts.yearEnd)
  const { data: papers, error: paperErr } = await paperQuery
  if (paperErr) return { ok: false, error: `Failed to fetch papers: ${paperErr.message}` }
  if (!papers || papers.length === 0) return { ok: true, test: emptyTest() }
  const paperIds = papers.map((p) => p.id as string)

  // Map each requested topic code to its normalized numeric id, keeping the
  // original code for the breakdown labels.
  const requestedTopics = (opts.topics ?? []).map((t) => t.trim()).filter(Boolean)
  const idToCode = new Map<string, string>()
  for (const code of requestedTopics) {
    for (const id of normalizeTopicCodes([code])) idToCode.set(id, code)
  }
  const topicIds = Array.from(idToCode.keys())

  // Candidate pool (larger than the final set so selection can spread it out).
  let q = sb
    .from("pages")
    .select(PAGE_SELECT)
    .eq("is_question", true)
    .not("qp_page_url", "is", null)
    .in("paper_id", paperIds)
    .order("page_number", { ascending: true })
    .limit(300)
  if (topicIds.length > 0) q = q.overlaps("topics", topicIds)
  if (opts.difficulty) q = q.eq("difficulty", opts.difficulty)

  const { data: pool, error: poolErr } = await q
  if (poolErr) return { ok: false, error: `Failed to fetch questions: ${poolErr.message}` }
  const rows = (pool ?? []) as unknown as PageRow[]
  if (rows.length === 0) return { ok: true, test: emptyTest() }

  // Bucket for an even spread: by requested topic when several are asked for,
  // otherwise by source paper so the set isn't all from one exam.
  const buckets = new Map<string, PageRow[]>()
  const bucketKey = (r: PageRow): string => {
    if (topicIds.length > 1) {
      const hit = topicIds.find((id) => (r.topics ?? []).includes(id))
      return hit ?? "other"
    }
    return r.paper_id ?? "other"
  }
  for (const r of rows) {
    const k = bucketKey(r)
    const b = buckets.get(k)
    if (b) b.push(r)
    else buckets.set(k, [r])
  }

  const selected = roundRobin(Array.from(buckets.values()), requestedCount)
  const idToName = await loadTopicIdToName(sb, resolved.id)
  const questions = selected.map((p) => mapPageRow(resolved.subject.name, idToName, p))

  // Breakdowns for the summary (topic names for readability).
  const topicBreakdown: Record<string, number> = {}
  const difficultyBreakdown: Record<string, number> = {}
  const years = new Set<number>()
  for (const p of selected) {
    for (const tid of p.topics ?? []) {
      // Only count requested topics when a topic filter was given.
      if (topicIds.length > 0 && !idToCode.has(tid)) continue
      const label = idToName.get(tid) ?? idToCode.get(tid) ?? tid
      topicBreakdown[label] = (topicBreakdown[label] ?? 0) + 1
    }
    difficultyBreakdown[p.difficulty || "unspecified"] =
      (difficultyBreakdown[p.difficulty || "unspecified"] ?? 0) + 1
    if (p.papers?.year) years.add(p.papers.year)
  }

  return {
    ok: true,
    test: {
      subject: resolved.subject.name,
      classified,
      requestedCount,
      selectedCount: questions.length,
      topicBreakdown,
      difficultyBreakdown,
      yearsCovered: Array.from(years).sort((a, b) => b - a),
      testBuilderUrl: `${SITE_ORIGIN}/test-builder`,
      questions,
    },
  }
}
