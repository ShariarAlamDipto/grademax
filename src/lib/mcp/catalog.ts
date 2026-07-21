// Read-only catalog helpers for the public MCP connector (/api/mcp).
//
// These functions back the connector's tools. They read the same build-time
// papers index the public catalog pages use (src/lib/papersIndex.ts) — a local
// file read, no Supabase round-trip and no auth. Nothing here may touch the
// service-role client or any cookie-authed /api route: the MCP surface is
// anonymous and must expose only what is already public on the site.

import {
  subjects,
  boardOf,
  boardDisplay,
  levelShort,
  type Board,
  type Level,
  type Subject,
} from "@/lib/subjects"
import {
  getPapersIndex,
  getSubjectSlugsWithPapers,
  type IndexedPaper,
} from "@/lib/papersIndex"
import {
  normalizePaperToken,
  formatPaperLabel,
  formatCambridgePaperLabel,
  cambridgePaperCode,
} from "@/lib/paper-slugs"
import { buildViewerHref, isAllowedPdfUrl } from "@/lib/viewer-link"

export const SITE_ORIGIN = "https://www.grademax.me"

export const VALID_SEASONS = [
  "jan",
  "jan-feb",
  "feb-mar",
  "may-jun",
  "oct-nov",
] as const
export type Season = (typeof VALID_SEASONS)[number]

/** A subject as surfaced to MCP clients. */
export interface SubjectSummary {
  slug: string
  name: string
  board: Board
  level: Level
  levelLabel: string
  /** Cambridge syllabus code, when applicable (e.g. "9702"). */
  examCode?: string
  /** True when the catalog has at least one published paper for this subject. */
  hasPapers: boolean
  catalogUrl: string
}

/** A single paper (question paper + mark scheme) as surfaced to MCP clients. */
export interface PaperResult {
  subjectSlug: string
  subjectName: string
  board: Board
  year: number
  season: Season
  paper: string
  paperLabel: string
  /** Cambridge component reference students search verbatim, e.g. "9702/22". */
  paperCode?: string
  questionPaperUrl: string | null
  markSchemeUrl: string | null
  /** On-site PDF viewer link (opens the QP, mark scheme toggle available). */
  viewerUrl: string | null
  /** Public catalog page for this paper's session. */
  catalogUrl: string
}

function findSubject(slugOrName: string): Subject | undefined {
  const needle = slugOrName.trim().toLowerCase()
  return subjects.find(
    (s) =>
      s.slug.toLowerCase() === needle ||
      s.name.toLowerCase() === needle ||
      normalizePaperToken(s.name) === normalizePaperToken(needle)
  )
}

function catalogUrlForSubject(s: Subject): string {
  const base =
    boardOf(s.level) === "cambridge" ? "/past-papers/cambridge" : "/past-papers"
  return `${SITE_ORIGIN}${base}/${s.slug}`
}

export async function listSubjects(opts: {
  board?: Board
  level?: Level
  withPapersOnly?: boolean
}): Promise<SubjectSummary[]> {
  const withPapers = await getSubjectSlugsWithPapers()
  return subjects
    .filter((s) => (opts.board ? boardOf(s.level) === opts.board : true))
    .filter((s) => (opts.level ? s.level === opts.level : true))
    .filter((s) => (opts.withPapersOnly ? withPapers.has(s.slug) : true))
    .map((s) => ({
      slug: s.slug,
      name: s.name,
      board: boardOf(s.level),
      level: s.level,
      levelLabel: `${boardDisplay(s.level)} ${levelShort(s.level)}`,
      examCode: s.examCode,
      hasPapers: withPapers.has(s.slug),
      catalogUrl: catalogUrlForSubject(s),
    }))
}

function toPaperResult(
  s: Subject,
  year: number,
  season: Season,
  p: IndexedPaper
): PaperResult {
  const board = boardOf(s.level)
  const paperLabel =
    board === "cambridge"
      ? formatCambridgePaperLabel(p.paperNumber)
      : formatPaperLabel(p.paperNumber)
  const catalogBase =
    board === "cambridge" ? "/past-papers/cambridge" : "/past-papers"
  const catalogUrl = `${SITE_ORIGIN}${catalogBase}/${s.slug}/${year}/${season}`

  const viewerHref =
    isAllowedPdfUrl(p.pdfUrl) || isAllowedPdfUrl(p.markschemePdfUrl)
      ? buildViewerHref({
          doc: isAllowedPdfUrl(p.pdfUrl) ? "qp" : "ms",
          qpUrl: p.pdfUrl,
          msUrl: p.markschemePdfUrl,
          title: `${s.name} ${year} ${season} ${paperLabel}`,
          backPath: `${catalogBase}/${s.slug}/${year}/${season}`,
        })
      : null

  return {
    subjectSlug: s.slug,
    subjectName: s.name,
    board,
    year,
    season,
    paper: p.paperNumber,
    paperLabel,
    paperCode:
      board === "cambridge"
        ? cambridgePaperCode(s.examCode, p.paperNumber)
        : undefined,
    questionPaperUrl: p.pdfUrl,
    markSchemeUrl: p.markschemePdfUrl,
    viewerUrl: viewerHref ? `${SITE_ORIGIN}${viewerHref}` : null,
    catalogUrl,
  }
}

export async function searchPapers(opts: {
  subject: string
  year?: number
  season?: Season
  paper?: string
  limit?: number
}): Promise<
  | { ok: true; subject: Subject; papers: PaperResult[] }
  | { ok: false; error: string }
> {
  const s = findSubject(opts.subject)
  if (!s) {
    return {
      ok: false,
      error: `Unknown subject "${opts.subject}". Use list_subjects to see valid slugs.`,
    }
  }

  const { bySession } = await getPapersIndex()
  const limit = Math.min(Math.max(opts.limit ?? 40, 1), 100)
  const paperToken = opts.paper ? normalizePaperToken(opts.paper) : null

  const results: PaperResult[] = []
  for (const [key, papers] of bySession) {
    const [slug, yearStr, season] = key.split("/")
    if (slug !== s.slug) continue
    const year = Number.parseInt(yearStr ?? "", 10)
    if (!Number.isInteger(year)) continue
    if (opts.year && year !== opts.year) continue
    if (opts.season && season !== opts.season) continue

    for (const p of papers) {
      if (paperToken && normalizePaperToken(p.paperNumber) !== paperToken) {
        continue
      }
      results.push(toPaperResult(s, year, season as Season, p))
    }
  }

  // Newest first, then by paper number.
  results.sort(
    (a, b) =>
      b.year - a.year ||
      a.season.localeCompare(b.season) ||
      a.paper.localeCompare(b.paper, undefined, { numeric: true })
  )

  return { ok: true, subject: s, papers: results.slice(0, limit) }
}

export async function getPaper(opts: {
  subject: string
  year: number
  season: Season
  paper: string
}): Promise<
  | { ok: true; paper: PaperResult }
  | { ok: false; error: string }
> {
  const found = await searchPapers({
    subject: opts.subject,
    year: opts.year,
    season: opts.season,
    paper: opts.paper,
    limit: 1,
  })
  if (!found.ok) return found
  if (found.papers.length === 0) {
    return {
      ok: false,
      error: `No paper found for ${opts.subject} ${opts.year} ${opts.season} paper "${opts.paper}". Use search_papers to see what exists for this subject.`,
    }
  }
  return { ok: true, paper: found.papers[0]! }
}
