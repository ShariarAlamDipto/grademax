import { createClient } from "@supabase/supabase-js"
import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { getSubjectBySlug, seasonDisplay, subjectColorClasses } from "@/lib/subjects"
import { seoSubjects } from "@/lib/seo-subjects"
import { toPaperSlug } from "@/lib/paper-slugs"

export const revalidate = 3600

function parseYearParam(value: string): number | null {
  if (!/^\d{4}$/.test(value)) return null
  const year = Number.parseInt(value, 10)
  if (year < 2000 || year > 2100) return null
  return year
}

export function generateStaticParams() {
  const popularSubjects = [
    "physics", "chemistry", "biology", "maths-a", "maths-b", "ict",
    "pure-mathematics-1", "mechanics-1", "statistics-1",
  ]
  const recentYears = ["2025", "2024", "2023", "2022", "2021"]
  return popularSubjects.flatMap((subject) => recentYears.map((year) => ({ subject, year })))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subject: string; year: string }>
}): Promise<Metadata> {
  const { subject: slug, year } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) return {}
  const parsedYear = parseYearParam(year)
  if (parsedYear === null) return {}
  const yearLabel = String(parsedYear)

  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const seoData = seoSubjects.find((s) => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const codeStr = examCode ? ` (${examCode})` : ""

  return {
    title: `Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} Past Papers by Session – Free PDF | GradeMax`,
    description:
      `Download free Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} past papers and mark schemes. ` +
      "Browse all available sessions and access official question papers as PDF.",
    openGraph: {
      title: `Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} Past Papers | GradeMax`,
      description: `Free Edexcel ${level} ${subj.name} ${yearLabel} past papers by session with mark schemes.`,
      url: `https://grademax.me/past-papers/${slug}/${yearLabel}`,
      siteName: "GradeMax",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${level} ${subj.name}${codeStr} ${yearLabel} Past Papers | GradeMax`,
      description: `Free Edexcel ${level} ${subj.name} ${yearLabel} papers by session.`,
    },
    alternates: {
      canonical: `https://grademax.me/past-papers/${slug}/${yearLabel}`,
    },
  }
}

interface PaperRow {
  id: string
  paper_number: string
  season: string
  pdf_url: string | null
  markscheme_pdf_url: string | null
}

interface SessionGroup {
  season: string
  displaySeason: string
  papers: PaperRow[]
}

const VALID_SEASONS = new Set(["jan", "jan-feb", "feb-mar", "may-jun", "oct-nov"])
const SEASON_ORDER: Record<string, number> = {
  jan: 0,
  "jan-feb": 0,
  "feb-mar": 1,
  "may-jun": 2,
  "oct-nov": 3,
}

function normalizeSeason(value: string): string {
  return value.trim().toLowerCase()
}

function isValidPublicUrl(url: string | null): url is string {
  if (!url) return false
  return /^https?:\/\//i.test(url)
}

function paperSort(a: string, b: string): number {
  const na = parseInt(a, 10)
  const nb = parseInt(b, 10)
  if (na !== nb) return na - nb
  return a.localeCompare(b)
}

function dedupeSessionPapers(sessionPapers: PaperRow[]): PaperRow[] {
  const byPaperNumber = new Map<string, PaperRow>()

  for (const paper of sessionPapers) {
    const existing = byPaperNumber.get(paper.paper_number)
    if (!existing) {
      byPaperNumber.set(paper.paper_number, paper)
      continue
    }

    const existingScore = Number(Boolean(existing.pdf_url)) + Number(Boolean(existing.markscheme_pdf_url))
    const paperScore = Number(Boolean(paper.pdf_url)) + Number(Boolean(paper.markscheme_pdf_url))

    if (paperScore > existingScore || (paperScore === existingScore && paper.id > existing.id)) {
      byPaperNumber.set(paper.paper_number, paper)
    }
  }

  return Array.from(byPaperNumber.values()).sort((a, b) => paperSort(a.paper_number, b.paper_number))
}

function buildJsonLd(slug: string, subjectName: string, level: string, year: string, sessions: SessionGroup[]) {
  const base = "https://grademax.me"
  const pageUrl = `${base}/past-papers/${slug}/${year}`

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "LearningResource",
        "@id": `${pageUrl}#resource`,
        name: `Edexcel ${level} ${subjectName} ${year} Past Papers`,
        description: `Free Edexcel ${level} ${subjectName} ${year} past papers organised by session.`,
        url: pageUrl,
        educationalLevel: level,
        learningResourceType: ["Past Paper", "Examination"],
        provider: {
          "@type": "Organization",
          name: "GradeMax",
          url: base,
        },
        isAccessibleForFree: true,
        inLanguage: "en-GB",
      },
      {
        "@type": "ItemList",
        name: `${subjectName} ${year} Sessions`,
        numberOfItems: sessions.length,
        itemListElement: sessions.map((session, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: `${subjectName} ${year} ${session.displaySeason}`,
          url: `${base}/past-papers/${slug}/${year}/${session.season}`,
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: base },
          { "@type": "ListItem", position: 2, name: "Past Papers", item: `${base}/past-papers` },
          { "@type": "ListItem", position: 3, name: subjectName, item: `${base}/past-papers/${slug}` },
          { "@type": "ListItem", position: 4, name: year, item: pageUrl },
        ],
      },
    ],
  }
}

function serializeJsonLd(schema: object): string {
  return JSON.stringify(schema).replace(/</g, "\\u003c")
}

export default async function SubjectYearPapersPage({
  params,
}: {
  params: Promise<{ subject: string; year: string }>
}) {
  const { subject: slug, year } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) notFound()

  const parsedYear = parseYearParam(year)
  if (parsedYear === null) notFound()
  const yearLabel = String(parsedYear)

  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const colorClass = subjectColorClasses[subj.colorKey]

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )

  const { data: subjectRow } = await supabase
    .from("subjects")
    .select("id")
    .eq("name", subj.name)
    .maybeSingle()

  if (!subjectRow) notFound()

  const { data } = await supabase
    .from("papers")
    .select("id, paper_number, season, pdf_url, markscheme_pdf_url")
    .eq("subject_id", subjectRow.id)
    .eq("year", parsedYear)
    .in("season", Array.from(VALID_SEASONS))
    .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")

  const papers = ((data as PaperRow[]) ?? [])
    .map((paper) => ({
      ...paper,
      season: normalizeSeason(paper.season),
      pdf_url: isValidPublicUrl(paper.pdf_url) ? paper.pdf_url : null,
      markscheme_pdf_url: isValidPublicUrl(paper.markscheme_pdf_url) ? paper.markscheme_pdf_url : null,
    }))
    .filter((paper) => VALID_SEASONS.has(paper.season))
    .filter((paper) => Boolean(paper.pdf_url) || Boolean(paper.markscheme_pdf_url))

  if (papers.length === 0) notFound()

  const sessionsBySeason = new Map<string, PaperRow[]>()
  for (const paper of papers) {
    if (!sessionsBySeason.has(paper.season)) sessionsBySeason.set(paper.season, [])
    sessionsBySeason.get(paper.season)!.push(paper)
  }

  const sessions: SessionGroup[] = Array.from(sessionsBySeason.entries())
    .sort(([a], [b]) => (SEASON_ORDER[a] ?? 9) - (SEASON_ORDER[b] ?? 9))
    .map(([season, rows]) => ({
      season,
      displaySeason: seasonDisplay(season),
      papers: dedupeSessionPapers(rows),
    }))
    .filter((session) => session.papers.length > 0)

  if (sessions.length === 0) notFound()

  const jsonLd = buildJsonLd(slug, subj.name, level, yearLabel, sessions)

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />

      <main className="min-h-screen bg-black text-white">
        <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-6 py-3 flex items-center gap-2 text-sm flex-wrap">
            <Link href="/past-papers" className="text-white/50 hover:text-white transition-colors">
              Past Papers
            </Link>
            <span className="text-white/20">›</span>
            <Link href={`/past-papers/${slug}`} className="text-white/50 hover:text-white transition-colors">
              {subj.name}
            </Link>
            <span className="text-white/20">›</span>
            <span className="text-white font-medium">{yearLabel}</span>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-6 py-10">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${colorClass}`}>
                Edexcel {level}
              </span>
              <span className="text-white/30 text-sm">{yearLabel}</span>
            </div>
            <h1 className="text-3xl font-extrabold mb-2">{subj.name} {yearLabel} Past Papers</h1>
            <p className="text-white/50">
              Browse all available {yearLabel} sessions for Edexcel {level} {subj.name}, with free question papers and mark schemes.
            </p>
          </div>

          <div className="space-y-6">
            {sessions.map((session) => (
              <div key={session.season} className="bg-white/[0.03] border border-white/10 rounded-xl p-5">
                <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-white/10">
                  <h2 className="text-base font-bold text-white/90">{session.displaySeason}</h2>
                  <Link
                    href={`/past-papers/${slug}/${yearLabel}/${session.season}`}
                    className="text-xs text-white/60 hover:text-white transition-colors"
                  >
                    Open session →
                  </Link>
                </div>

                <div className="space-y-2">
                  {session.papers.map((paper) => {
                    const paperSlug = toPaperSlug(paper.paper_number)
                    return (
                      <div
                        key={paper.id}
                        className="bg-white/[0.03] border border-white/10 rounded-lg px-4 py-3 flex items-center justify-between gap-3"
                      >
                        {paperSlug ? (
                          <Link
                            href={`/past-papers/${slug}/${yearLabel}/${session.season}/${paperSlug}`}
                            className="font-semibold text-white hover:text-white/80 transition-colors"
                          >
                            Paper {paper.paper_number}
                          </Link>
                        ) : (
                          <span className="font-semibold text-white/80">Paper {paper.paper_number}</span>
                        )}

                        <div className="flex gap-2 flex-wrap">
                          {paper.pdf_url && (
                            <a
                              href={paper.pdf_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30 hover:bg-blue-500/25 transition-colors"
                            >
                              Question Paper
                            </a>
                          )}
                          {paper.markscheme_pdf_url && (
                            <a
                              href={paper.markscheme_pdf_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30 hover:bg-emerald-500/25 transition-colors"
                            >
                              Mark Scheme
                            </a>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-10 pt-6 border-t border-white/10">
            <Link
              href={`/past-papers/${slug}`}
              className="text-sm text-white/50 hover:text-white transition-colors"
            >
              ← All {subj.name} Past Papers
            </Link>
          </div>
        </div>
      </main>
    </>
  )
}
