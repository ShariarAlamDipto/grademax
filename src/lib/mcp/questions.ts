// DB-backed catalog helpers for the public MCP connector (/api/mcp).
//
// Unlike catalog.ts (which reads the static build-time papers index), these
// tools read live Supabase tables — but only through the ANON key, and only
// tables that are already public on the site (proven by /api/subjects and
// /api/topics, which use the same key). No service-role client, no cookies.
//
// Question-level data lives in the `pages` table (is_question = true), keyed to
// `papers` by paper_id. Only six subjects are classified with topics; the rest
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
  topics: string[]
  difficulty: string
  year: number | null
  season: string | null
  paper: string | null
  hasDiagram: boolean
  textExcerpt: string
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
    .select(
      `id,page_number,question_number,topics,difficulty,qp_page_url,ms_page_url,has_diagram,text_excerpt,
       papers(year,season,paper_number)`,
      { count: "exact" }
    )
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
  const questions: QuestionResult[] = rows.map((p) => {
    const qp = toAbsolutePdfUrl(p.qp_page_url)
    const ms = toAbsolutePdfUrl(p.ms_page_url)
    const viewerHref =
      isAllowedPdfUrl(qp) || isAllowedPdfUrl(ms)
        ? buildViewerHref({
            doc: isAllowedPdfUrl(qp) ? "qp" : "ms",
            qpUrl: qp,
            msUrl: ms,
            title: `${resolved.subject.name} ${p.papers?.year ?? ""} ${p.papers?.season ?? ""} Q${p.question_number ?? p.page_number}`.trim(),
            backPath: "/test-builder",
          })
        : null
    return {
      id: p.id,
      questionNumber: p.question_number || String(p.page_number),
      topics: p.topics ?? [],
      difficulty: p.difficulty || "unknown",
      year: p.papers?.year ?? null,
      season: p.papers?.season ?? null,
      paper: p.papers?.paper_number ?? null,
      hasDiagram: p.has_diagram ?? false,
      textExcerpt: (p.text_excerpt ?? "").slice(0, 500),
      questionPdfUrl: qp,
      markSchemePdfUrl: ms,
      viewerUrl: viewerHref ? `${SITE_ORIGIN}${viewerHref}` : null,
    }
  })

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
