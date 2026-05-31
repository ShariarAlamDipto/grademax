import { createClient } from "@supabase/supabase-js"
import { subjects } from "@/lib/subjects"
import { normalizePaperToken, toPaperSlug } from "@/lib/paper-slugs"

const VALID_SEASONS = new Set(["jan", "jan-feb", "feb-mar", "may-jun", "oct-nov"])

export interface IndexedPaper {
  id: string
  paperNumber: string
  pdfUrl: string | null
  markschemePdfUrl: string | null
}

export interface PapersIndex {
  /** key = `${subjectSlug}/${year}/${season}` -> deduped, sorted list */
  bySession: Map<string, IndexedPaper[]>
  /** key = `${subjectSlug}/${year}/${season}/${paperSlug}` -> best paper */
  byLeaf: Map<string, IndexedPaper>
  /** key = subjectSlug -> set of years that have at least one published paper */
  yearsBySubject: Map<string, Set<number>>
}

function isValidPublicUrl(url: string | null): url is string {
  if (!url) return false
  return /^https?:\/\//i.test(url)
}

function paperSort(a: string, b: string): number {
  const na = parseInt(a, 10)
  const nb = parseInt(b, 10)
  if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb
  return a.localeCompare(b)
}

function pickBetter(a: IndexedPaper, b: IndexedPaper): IndexedPaper {
  const sa = Number(Boolean(a.pdfUrl)) + Number(Boolean(a.markschemePdfUrl))
  const sb = Number(Boolean(b.pdfUrl)) + Number(Boolean(b.markschemePdfUrl))
  if (sb > sa) return b
  if (sb === sa && b.id > a.id) return b
  return a
}

let cachedPromise: Promise<PapersIndex> | null = null

export function getPapersIndex(): Promise<PapersIndex> {
  if (!cachedPromise) cachedPromise = loadIndex()
  return cachedPromise
}

async function loadIndex(): Promise<PapersIndex> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  const empty: PapersIndex = { bySession: new Map(), byLeaf: new Map(), yearsBySubject: new Map() }
  if (!url || !key) return empty

  const subjectNameToSlug = new Map(subjects.map((s) => [s.name, s.slug]))
  const supabase = createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  const bySessionRaw = new Map<string, IndexedPaper[]>()
  const byLeaf = new Map<string, IndexedPaper>()

  type Row = {
    id: string
    year: number
    season: string
    paper_number: string
    pdf_url: string | null
    markscheme_pdf_url: string | null
    subjects: { name: string } | { name: string }[]
  }

  const pageSize = 1000
  let lastSeenId: string | null = null

  try {
    while (true) {
      let q = supabase
        .from("papers")
        .select("id,year,season,paper_number,pdf_url,markscheme_pdf_url,subjects!inner(name)")
        .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
        .order("id", { ascending: true })
        .limit(pageSize)
      if (lastSeenId) q = q.gt("id", lastSeenId)

      const { data, error } = await q
      if (error || !data || data.length === 0) break

      for (const row of data as Row[]) {
        const subj = Array.isArray(row.subjects) ? row.subjects[0] : row.subjects
        const slug = subj?.name ? subjectNameToSlug.get(subj.name) : undefined
        if (!slug) continue
        const season = (row.season ?? "").toLowerCase()
        if (!VALID_SEASONS.has(season)) continue

        const pdf = isValidPublicUrl(row.pdf_url) ? row.pdf_url : null
        const ms = isValidPublicUrl(row.markscheme_pdf_url) ? row.markscheme_pdf_url : null
        if (!pdf && !ms) continue

        const paper: IndexedPaper = {
          id: row.id,
          paperNumber: row.paper_number,
          pdfUrl: pdf,
          markschemePdfUrl: ms,
        }

        const sessionKey = `${slug}/${row.year}/${season}`
        const list = bySessionRaw.get(sessionKey)
        if (list) list.push(paper)
        else bySessionRaw.set(sessionKey, [paper])

        const paperSlug = toPaperSlug(row.paper_number)
        if (paperSlug) {
          const leafKey = `${sessionKey}/${paperSlug}`
          const existing = byLeaf.get(leafKey)
          byLeaf.set(leafKey, existing ? pickBetter(existing, paper) : paper)
        }
      }

      lastSeenId = (data[data.length - 1] as Row).id
      if (data.length < pageSize) break
    }
  } catch {
    return empty
  }

  const bySession = new Map<string, IndexedPaper[]>()
  const yearsBySubject = new Map<string, Set<number>>()
  for (const [key, list] of bySessionRaw) {
    const byNum = new Map<string, IndexedPaper>()
    for (const p of list) {
      const existing = byNum.get(p.paperNumber)
      byNum.set(p.paperNumber, existing ? pickBetter(existing, p) : p)
    }
    bySession.set(
      key,
      Array.from(byNum.values()).sort((a, b) => paperSort(a.paperNumber, b.paperNumber))
    )
    // key = subjectSlug/year/season — pull year out
    const [subjectSlug, yearStr] = key.split("/")
    const yearNum = Number.parseInt(yearStr ?? "", 10)
    if (subjectSlug && Number.isInteger(yearNum)) {
      let set = yearsBySubject.get(subjectSlug)
      if (!set) {
        set = new Set()
        yearsBySubject.set(subjectSlug, set)
      }
      set.add(yearNum)
    }
  }

  return { bySession, byLeaf, yearsBySubject }
}

export function leafKey(subjectSlug: string, year: string | number, season: string, paperSlug: string): string {
  return `${subjectSlug}/${year}/${season}/${paperSlug}`
}

export function sessionKey(subjectSlug: string, year: string | number, season: string): string {
  return `${subjectSlug}/${year}/${season}`
}

export function findByPaperToken(
  papers: IndexedPaper[],
  paperToken: string
): IndexedPaper | null {
  const matches = papers.filter((p) => normalizePaperToken(p.paperNumber) === paperToken)
  if (matches.length === 0) return null
  return matches.reduce(pickBetter)
}
