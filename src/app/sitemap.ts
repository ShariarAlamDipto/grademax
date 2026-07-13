import { MetadataRoute } from 'next'
import { createClient } from '@supabase/supabase-js'
import { seoSubjects, type SEOSubject } from '@/lib/seo-subjects'
import { pastPaperSubjects, subjects, dbNameOf } from '@/lib/subjects'
import { toPaperSlug } from '@/lib/paper-slugs'

const BASE_URL = 'https://www.grademax.me'
const VALID_SEASONS = new Set(['jan', 'jan-feb', 'feb-mar', 'may-jun', 'oct-nov'])

// Build a DB-name → slug map for quick lookup (Cambridge subjects store a
// board-prefixed name in the DB, so key on dbNameOf rather than display name)
const slugByName = new Map(subjects.map(s => [dbNameOf(s), s.slug]))

function normalizeSeason(value: unknown): string {
  return String(value ?? '').trim().toLowerCase()
}

function parseSitemapYear(value: unknown): number | null {
  let year: number
  if (typeof value === 'number') {
    year = value
  } else {
    const raw = String(value ?? '').trim()
    if (!/^\d{4}$/.test(raw)) return null
    year = Number.parseInt(raw, 10)
  }
  if (!Number.isInteger(year)) return null
  if (year < 2000 || year > 2100) return null
  return year
}

function isValidPublicUrl(value: unknown): boolean {
  const raw = String(value ?? '').trim()
  return /^https?:\/\//i.test(raw)
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // NOTE: evergreen pages intentionally omit lastModified. Claiming every URL
  // changed "right now" on every build trains crawlers to distrust lastmod;
  // dynamic paper pages below report their real papers.created_at instead.

  // ─── Core pages ──────────────────────────────────────────────────────────────

  const corePages: MetadataRoute.Sitemap = [
    { url: BASE_URL,                              changeFrequency: 'weekly',  priority: 1    },
    { url: `${BASE_URL}/edexcel-past-papers`,     changeFrequency: 'weekly',  priority: 0.95 },
    { url: `${BASE_URL}/edexcel-igcse-past-papers`, changeFrequency: 'weekly', priority: 0.95 },
    { url: `${BASE_URL}/edexcel-a-level-past-papers`, changeFrequency: 'weekly', priority: 0.95 },
    { url: `${BASE_URL}/edexcel-worksheets`,      changeFrequency: 'weekly',  priority: 0.95 },
    { url: `${BASE_URL}/subjects`,                changeFrequency: 'weekly',  priority: 0.9  },
    // /generate is auth-gated (307 → /login) so it must NOT be in the sitemap;
    // /edexcel-worksheets above is its public, indexable landing page.
    // /test-builder renders a public landing for logged-out visitors.
    { url: `${BASE_URL}/test-builder`,            changeFrequency: 'weekly',  priority: 0.9  },
    { url: `${BASE_URL}/browse`,                  changeFrequency: 'weekly',  priority: 0.8  },
    { url: `${BASE_URL}/past-papers`,             changeFrequency: 'weekly',  priority: 0.9  },
    { url: `${BASE_URL}/past-papers/cambridge`,   changeFrequency: 'weekly',  priority: 0.9  },
    { url: `${BASE_URL}/about`,                   changeFrequency: 'monthly', priority: 0.6  },
    { url: `${BASE_URL}/contact`,                 changeFrequency: 'monthly', priority: 0.5  },
    { url: `${BASE_URL}/blog`,                    changeFrequency: 'weekly',  priority: 0.7  },
    { url: `${BASE_URL}/privacy`,                 changeFrequency: 'yearly',  priority: 0.3  },
    { url: `${BASE_URL}/terms`,                   changeFrequency: 'yearly',  priority: 0.3  },
  ]

  // ─── Blog article pages ───────────────────────────────────────────────────────

  const blogSlugs = [
    'how-to-use-past-papers-effectively',
    'edexcel-igcse-physics-revision-guide',
    'edexcel-igcse-maths-a-revision-guide',
    'how-to-get-a-star-igcse-chemistry',
    'pure-maths-1-wma11-revision-tips',
    'edexcel-vs-cambridge-igcse-differences',
    'igcse-biology-paper-2-tips',
    'revision-timetable-igcse-a-level',
  ]

  const blogPages: MetadataRoute.Sitemap = blogSlugs.map(slug => ({
    url: `${BASE_URL}/blog/${slug}`,
    changeFrequency: 'monthly' as const,
    priority: 0.65,
  }))

  // ─── Level landing pages ──────────────────────────────────────────────────────

  const levelPages: MetadataRoute.Sitemap = [
    { url: `${BASE_URL}/subjects/igcse`, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE_URL}/subjects/ial`,   changeFrequency: 'weekly', priority: 0.9 },
  ]

  // ─── SEO subject pages ───────────────────────────────────────────────────────

  const subjectPages: MetadataRoute.Sitemap = seoSubjects.map((s: SEOSubject) => ({
    url: `${BASE_URL}/subjects/${s.level}/${s.slug}`,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  const topicPages: MetadataRoute.Sitemap = seoSubjects.flatMap((s: SEOSubject) =>
    s.topics.map(t => ({
      url: `${BASE_URL}/subjects/${s.level}/${s.slug}/${t.slug}`,
      changeFrequency: 'weekly' as const,
      priority: 0.75,
    }))
  )

  // ─── Past paper subject pages ─────────────────────────────────────────────────

  const pastPaperSubjectPages: MetadataRoute.Sitemap = pastPaperSubjects.map(s => ({
    url: `${BASE_URL}/past-papers/${s.slug}`,
    changeFrequency: 'monthly' as const,
    priority: 0.9,
  }))

  // ─── Dynamic: session pages + individual paper pages (fetched from Supabase) ──
  // Session pages  → /past-papers/{slug}/{year}/{season}
  // Paper pages    → /past-papers/{slug}/{year}/{season}/paper-{number}
  // These let Google index every specific paper, enabling queries like
  // "Edexcel IGCSE Physics 2025 January Paper 1".

  const yearPages: MetadataRoute.Sitemap = []
  const sessionPages: MetadataRoute.Sitemap = []
  const paperPages: MetadataRoute.Sitemap = []

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      { auth: { autoRefreshToken: false, persistSession: false } }
    )

    // Fetch ALL papers with a file. Supabase caps a single response at 1000 rows
    // and there are ~11k qualifying papers, so page through by id — otherwise the
    // sitemap silently omits ~90% of the individual paper/session/year pages.
    type PaperRow = {
      year: string | number | null
      season: string | null
      paper_number: string | number | null
      pdf_url: string | null
      markscheme_pdf_url: string | null
      created_at: string | null
      subjects: { name: string } | { name: string }[] | null
    }
    const PAGE_SIZE = 1000
    const data: PaperRow[] = []
    for (let from = 0; ; from += PAGE_SIZE) {
      const { data: page, error } = await supabase
        .from('papers')
        .select('year, season, paper_number, pdf_url, markscheme_pdf_url, created_at, subjects!inner(name)')
        .or('pdf_url.not.is.null,markscheme_pdf_url.not.is.null')
        .order('id', { ascending: true })
        .range(from, from + PAGE_SIZE - 1)
      if (error) throw error
      if (!page || page.length === 0) break
      data.push(...(page as PaperRow[]))
      if (page.length < PAGE_SIZE) break
    }

    if (data.length > 0) {
      // key → most recent papers.created_at in that group, so lastmod reflects
      // when content actually changed rather than when the site last built.
      const yearDates = new Map<string, Date>()
      const sessionDates = new Map<string, Date>()
      const paperDates = new Map<string, Date>()

      const bumpDate = (map: Map<string, Date>, key: string, date: Date | null) => {
        const existing = map.get(key)
        if (!existing || (date && date > existing)) {
          map.set(key, date ?? existing ?? new Date(0))
        }
      }

      for (const row of data) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const subjectName: string = (row.subjects as any)?.name ?? ''
        const slug = slugByName.get(subjectName)
        if (!slug) continue
        const hasRenderableFile = isValidPublicUrl(row.pdf_url) || isValidPublicUrl(row.markscheme_pdf_url)
        if (!hasRenderableFile) continue
        const year = parseSitemapYear(row.year)
        if (year === null) continue
        const season = normalizeSeason(row.season)
        if (!VALID_SEASONS.has(season)) continue

        const createdAt = row.created_at ? new Date(row.created_at) : null
        const validCreatedAt = createdAt && !Number.isNaN(createdAt.getTime()) ? createdAt : null

        bumpDate(yearDates, `${slug}/${year}`, validCreatedAt)
        bumpDate(sessionDates, `${slug}/${year}/${season}`, validCreatedAt)

        const paperSlug = toPaperSlug(row.paper_number)
        if (!paperSlug) continue
        bumpDate(paperDates, `${slug}/${year}/${season}/${paperSlug}`, validCreatedAt)
      }

      const toEntry = (
        key: string,
        date: Date,
        changeFrequency: 'monthly' | 'yearly',
        priority: number,
      ): MetadataRoute.Sitemap[number] => ({
        url: `${BASE_URL}/past-papers/${key}`,
        ...(date.getTime() > 0 ? { lastModified: date } : {}),
        changeFrequency,
        priority,
      })

      for (const [key, date] of yearDates)    yearPages.push(toEntry(key, date, 'monthly', 0.88))
      for (const [key, date] of sessionDates) sessionPages.push(toEntry(key, date, 'monthly', 0.9))
      for (const [key, date] of paperDates)   paperPages.push(toEntry(key, date, 'yearly', 0.85))
    }
  } catch {
    // Non-fatal — sitemap will still generate without dynamic pages
    console.warn('sitemap: could not fetch paper pages from Supabase')
  }

  // Conservative fallback if dynamic fetch is unavailable:
  // keep year-level discoverability using known SEO subject year ranges.
  const fallbackYearPages: MetadataRoute.Sitemap = []
  if (yearPages.length === 0) {
    const seenFallbackYears = new Set<string>()

    for (const subject of seoSubjects) {
      for (const year of subject.yearsAvailable) {
        const parsedYear = parseSitemapYear(year)
        if (parsedYear === null) continue

        const key = `${subject.slug}/${parsedYear}`
        if (seenFallbackYears.has(key)) continue
        seenFallbackYears.add(key)

        fallbackYearPages.push({
          url: `${BASE_URL}/past-papers/${key}`,
          changeFrequency: 'monthly' as const,
          priority: 0.84,
        })
      }
    }
  }

  // ─── SEO "QP" landing pages ───────────────────────────────────────────────────

  const qpPages: MetadataRoute.Sitemap = seoSubjects.flatMap((s: SEOSubject) => {
    const levelPrefix = s.level === 'igcse' ? 'igcse' : 'a-level'
    return [
      { url: `${BASE_URL}/qp/${levelPrefix}-${s.slug}`,                     changeFrequency: 'weekly' as const, priority: 0.9 },
      { url: `${BASE_URL}/qp/${levelPrefix}-${s.slug}-past-papers`,         changeFrequency: 'weekly' as const, priority: 0.9 },
      { url: `${BASE_URL}/qp/${levelPrefix}-${s.slug}-question-papers`,     changeFrequency: 'weekly' as const, priority: 0.85 },
      { url: `${BASE_URL}/qp/${s.examCode.toLowerCase()}`,                  changeFrequency: 'weekly' as const, priority: 0.85 },
      { url: `${BASE_URL}/qp/${s.examCode.toLowerCase()}-past-papers`,      changeFrequency: 'weekly' as const, priority: 0.85 },
    ]
  })

  return [
    ...corePages,
    ...blogPages,
    ...levelPages,
    ...subjectPages,
    ...topicPages,
    ...pastPaperSubjectPages,
    ...(yearPages.length > 0 ? yearPages : fallbackYearPages),
    ...sessionPages,
    ...paperPages,             // ← individual paper pages (year/season/paper-N)
    ...qpPages,
  ]
}
