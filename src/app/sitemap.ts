import { MetadataRoute } from 'next'
import { createClient } from '@supabase/supabase-js'
import { seoSubjects, type SEOSubject } from '@/lib/seo-subjects'
import { pastPaperSubjects, subjects } from '@/lib/subjects'
import { toPaperSlug } from '@/lib/paper-slugs'

const BASE_URL = 'https://grademax.me'
const VALID_SEASONS = new Set(['jan', 'jan-feb', 'feb-mar', 'may-jun', 'oct-nov'])

// Build a slug → subject map for quick lookup
const slugByName = new Map(subjects.map(s => [s.name, s.slug]))

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
  const now = new Date()

  // ─── Core pages ──────────────────────────────────────────────────────────────

  const corePages: MetadataRoute.Sitemap = [
    { url: BASE_URL,                              lastModified: now, changeFrequency: 'weekly',  priority: 1    },
    { url: `${BASE_URL}/edexcel-past-papers`,     lastModified: now, changeFrequency: 'weekly',  priority: 0.95 },
    { url: `${BASE_URL}/edexcel-igcse-past-papers`, lastModified: now, changeFrequency: 'weekly', priority: 0.95 },
    { url: `${BASE_URL}/edexcel-a-level-past-papers`, lastModified: now, changeFrequency: 'weekly', priority: 0.95 },
    { url: `${BASE_URL}/edexcel-worksheets`,      lastModified: now, changeFrequency: 'weekly',  priority: 0.95 },
    { url: `${BASE_URL}/subjects`,                lastModified: now, changeFrequency: 'weekly',  priority: 0.9  },
    { url: `${BASE_URL}/generate`,                lastModified: now, changeFrequency: 'weekly',  priority: 0.9  },
    { url: `${BASE_URL}/browse`,                  lastModified: now, changeFrequency: 'weekly',  priority: 0.8  },
    { url: `${BASE_URL}/past-papers`,             lastModified: now, changeFrequency: 'weekly',  priority: 0.9  },
    { url: `${BASE_URL}/about`,                   lastModified: now, changeFrequency: 'monthly', priority: 0.6  },
    { url: `${BASE_URL}/contact`,                 lastModified: now, changeFrequency: 'monthly', priority: 0.5  },
    { url: `${BASE_URL}/privacy`,                 lastModified: now, changeFrequency: 'yearly',  priority: 0.3  },
    { url: `${BASE_URL}/terms`,                   lastModified: now, changeFrequency: 'yearly',  priority: 0.3  },
  ]

  // ─── Level landing pages ──────────────────────────────────────────────────────

  const levelPages: MetadataRoute.Sitemap = [
    { url: `${BASE_URL}/subjects/igcse`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE_URL}/subjects/ial`,   lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
  ]

  // ─── SEO subject pages ───────────────────────────────────────────────────────

  const subjectPages: MetadataRoute.Sitemap = seoSubjects.map((s: SEOSubject) => ({
    url: `${BASE_URL}/subjects/${s.level}/${s.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  const topicPages: MetadataRoute.Sitemap = seoSubjects.flatMap((s: SEOSubject) =>
    s.topics.map(t => ({
      url: `${BASE_URL}/subjects/${s.level}/${s.slug}/${t.slug}`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: 0.75,
    }))
  )

  // ─── Past paper subject pages ─────────────────────────────────────────────────

  const pastPaperSubjectPages: MetadataRoute.Sitemap = pastPaperSubjects.map(s => ({
    url: `${BASE_URL}/past-papers/${s.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.9,
  }))

  // ─── Paper number hub pages (/past-papers/{subject}/paper-N) ─────────────────
  // These aggregate all years for a specific paper number — high-value SEO targets
  // e.g. "Physics Paper 1 past papers" → /past-papers/physics/paper-1

  const paperHubPages: MetadataRoute.Sitemap = pastPaperSubjects.flatMap((s) =>
    ["1", "2", "3", "4"].map((n) => ({
      url: `${BASE_URL}/past-papers/${s.slug}/paper-${n}`,
      lastModified: now,
      changeFrequency: 'monthly' as const,
      priority: 0.88,
    }))
  )

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

    // Fetch all papers with at least one file, including paper_number for individual pages
    const { data } = await supabase
      .from('papers')
      .select('year, season, paper_number, pdf_url, markscheme_pdf_url, subjects!inner(name)')
      .or('pdf_url.not.is.null,markscheme_pdf_url.not.is.null')

    if (data) {
      const seenYears = new Set<string>()
      const seenSessions = new Set<string>()
      const seenPapers = new Set<string>()

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

        // Year-level page
        const yearKey = `${slug}/${year}`
        if (!seenYears.has(yearKey)) {
          seenYears.add(yearKey)
          yearPages.push({
            url: `${BASE_URL}/past-papers/${yearKey}`,
            lastModified: now,
            changeFrequency: 'monthly' as const,
            priority: 0.88,
          })
        }

        // Session-level page
        const sessionKey = `${slug}/${year}/${season}`
        if (!seenSessions.has(sessionKey)) {
          seenSessions.add(sessionKey)
          sessionPages.push({
            url: `${BASE_URL}/past-papers/${sessionKey}`,
            lastModified: now,
            changeFrequency: 'monthly' as const,
            priority: 0.9,
          })
        }

        // Individual paper page
        const paperSlug = toPaperSlug(row.paper_number)
        if (!paperSlug) continue
        const paperKey = `${slug}/${year}/${season}/${paperSlug}`
        if (!seenPapers.has(paperKey)) {
          seenPapers.add(paperKey)
          paperPages.push({
            url: `${BASE_URL}/past-papers/${paperKey}`,
            lastModified: now,
            changeFrequency: 'yearly' as const,
            priority: 0.85,
          })
        }
      }
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
          lastModified: now,
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
      { url: `${BASE_URL}/qp/${levelPrefix}-${s.slug}`,                     lastModified: now, changeFrequency: 'weekly' as const, priority: 0.9 },
      { url: `${BASE_URL}/qp/${levelPrefix}-${s.slug}-past-papers`,         lastModified: now, changeFrequency: 'weekly' as const, priority: 0.9 },
      { url: `${BASE_URL}/qp/${levelPrefix}-${s.slug}-question-papers`,     lastModified: now, changeFrequency: 'weekly' as const, priority: 0.85 },
      { url: `${BASE_URL}/qp/${s.examCode.toLowerCase()}`,                  lastModified: now, changeFrequency: 'weekly' as const, priority: 0.85 },
      { url: `${BASE_URL}/qp/${s.examCode.toLowerCase()}-past-papers`,      lastModified: now, changeFrequency: 'weekly' as const, priority: 0.85 },
    ]
  })

  return [
    ...corePages,
    ...levelPages,
    ...subjectPages,
    ...topicPages,
    ...pastPaperSubjectPages,
    ...paperHubPages,          // ← paper number hubs (paper-1 through paper-4)
    ...(yearPages.length > 0 ? yearPages : fallbackYearPages),
    ...sessionPages,
    ...paperPages,             // ← individual paper pages (year/season/paper-N)
    ...qpPages,
  ]
}
