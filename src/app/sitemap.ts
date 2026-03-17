import { MetadataRoute } from 'next'
import { createClient } from '@supabase/supabase-js'
import { seoSubjects, type SEOSubject } from '@/lib/seo-subjects'
import { pastPaperSubjects, subjects } from '@/lib/subjects'

const BASE_URL = 'https://grademax.me'

// Build a slug → subject map for quick lookup
const slugByName = new Map(subjects.map(s => [s.name, s.slug]))

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

  // ─── Dynamic: individual paper session pages (fetched from Supabase) ──────────
  // These give Google specific year+season pages to index, enabling rich results
  // like "Edexcel IGCSE Maths B 2023 January Past Papers".

  const sessionPages: MetadataRoute.Sitemap = []

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      { auth: { autoRefreshToken: false, persistSession: false } }
    )

    // Fetch all distinct subject / year / season combos with at least one paper
    const { data } = await supabase
      .from('papers')
      .select('year, season, subjects!inner(name)')
      .or('pdf_url.not.is.null,markscheme_pdf_url.not.is.null')

    if (data) {
      // Deduplicate
      const seen = new Set<string>()
      for (const row of data) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const subjectName: string = (row.subjects as any)?.name ?? ''
        const slug = slugByName.get(subjectName)
        if (!slug) continue

        const key = `${slug}/${row.year}/${row.season}`
        if (seen.has(key)) continue
        seen.add(key)

        sessionPages.push({
          url: `${BASE_URL}/past-papers/${key}`,
          lastModified: now,
          changeFrequency: 'monthly' as const,
          priority: 0.9,
        })
      }
    }
  } catch {
    // Non-fatal — sitemap will still generate without session pages
    console.warn('sitemap: could not fetch session pages from Supabase')
  }

  // ─── SEO "QP" landing pages ───────────────────────────────────────────────────

  const seoPastPaperPages: MetadataRoute.Sitemap = seoSubjects.map((s: SEOSubject) => ({
    url: `${BASE_URL}/past-papers/${s.level}/${s.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }))

  const pastPaperYearPages: MetadataRoute.Sitemap = seoSubjects.flatMap((s: SEOSubject) =>
    s.yearsAvailable.map(year => ({
      url: `${BASE_URL}/past-papers/${s.level}/${s.slug}/${year}`,
      lastModified: now,
      changeFrequency: 'yearly' as const,
      priority: 0.6,
    }))
  )

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
    ...sessionPages,          // ← new: individual year/season pages
    ...seoPastPaperPages,
    ...pastPaperYearPages,
    ...qpPages,
  ]
}
