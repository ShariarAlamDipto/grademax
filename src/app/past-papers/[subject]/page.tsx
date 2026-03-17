import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import {
  pastPaperSubjects,
  getSubjectBySlug,
  subjectColorClasses,
  seasonDisplay,
} from "@/lib/subjects"

export const revalidate = 3600

// ─── Static params ─────────────────────────────────────────────────────────────

export async function generateStaticParams() {
  return pastPaperSubjects.map((s) => ({ subject: s.slug }))
}

// ─── Metadata ──────────────────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subject: string }>
}) {
  const { subject: slug } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) return {}

  const level = subj.level === "ial" ? "A Level" : "IGCSE"

  return {
    title: `Edexcel ${level} ${subj.name} Past Papers – Free Download with Mark Schemes`,
    description: `Download free Edexcel ${level} ${subj.name} past papers and mark schemes from 2011 to 2025. All question papers organized by year and session.`,
    keywords: [
      `${subj.name} past papers`,
      `${level} ${subj.name} past papers`,
      `Edexcel ${subj.name} past papers`,
      `${subj.name} question papers`,
      `${subj.name} mark scheme`,
      `${subj.name} past papers free download`,
      `Edexcel ${subj.name} ${level}`,
    ],
    openGraph: {
      title: `Edexcel ${level} ${subj.name} Past Papers | GradeMax`,
      description: `Download free ${subj.name} past papers with mark schemes. ${level} papers from 2011-2025.`,
      url: `https://grademax.me/past-papers/${slug}`,
      siteName: "GradeMax",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${level} ${subj.name} Past Papers | GradeMax`,
      description: `Free Edexcel ${level} ${subj.name} past papers with mark schemes.`,
    },
    alternates: {
      canonical: `https://grademax.me/past-papers/${slug}`,
    },
  }
}

// ─── Types ─────────────────────────────────────────────────────────────────────

interface PaperRow {
  id: string
  paper_number: string
  year: number
  season: string
  pdf_url: string | null
  markscheme_pdf_url: string | null
}

interface SessionGroup {
  season: string
  displaySeason: string
  papers: PaperRow[]
}

interface YearGroup {
  year: number
  sessions: SessionGroup[]
}

const VALID_SEASONS = new Set(["jan", "jan-feb", "feb-mar", "may-jun", "oct-nov"])

function normalizeSeason(season: string): string {
  return season.trim().toLowerCase()
}

function isValidPublicUrl(url: string | null): url is string {
  if (!url) return false
  return /^https?:\/\//i.test(url)
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

// ─── Helpers ───────────────────────────────────────────────────────────────────

function paperSort(a: string, b: string): number {
  const na = parseInt(a), nb = parseInt(b)
  if (na !== nb) return na - nb
  return a.localeCompare(b)
}

const SEASON_ORDER: Record<string, number> = {
  jan: 0, "jan-feb": 0, "feb-mar": 1, "may-jun": 2, "oct-nov": 3,
}

// ─── JSON-LD ───────────────────────────────────────────────────────────────────

function buildJsonLd(slug: string, subjectName: string, level: string, yearGroups: YearGroup[]) {
  const BASE = "https://grademax.me"
  const pageUrl = `${BASE}/past-papers/${slug}`

  // ItemList of all available sessions
  const sessionItems = yearGroups.flatMap((yg, yi) =>
    yg.sessions.map((sess, si) => ({
      "@type": "ListItem",
      position: yi * 10 + si + 1,
      name: `${subjectName} ${yg.year} ${sess.displaySeason} Past Papers`,
      url: `${BASE}/past-papers/${slug}/${yg.year}/${sess.season}`,
    }))
  )

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "LearningResource",
        "@id": `${pageUrl}#resource`,
        name: `Edexcel ${level} ${subjectName} Past Papers`,
        description: `Free Edexcel ${level} ${subjectName} past papers and mark schemes from 2011 to 2025, organised by year and session.`,
        url: pageUrl,
        educationalLevel: level,
        learningResourceType: ["Past Paper", "Examination"],
        provider: {
          "@type": "Organization",
          name: "GradeMax",
          url: BASE,
        },
        isAccessibleForFree: true,
        inLanguage: "en-GB",
        educationalAlignment: {
          "@type": "AlignmentObject",
          alignmentType: "educationalSubject",
          targetName: subjectName,
          educationalFramework: "Edexcel",
        },
      },
      {
        "@type": "ItemList",
        name: `${subjectName} Past Paper Sessions`,
        numberOfItems: sessionItems.length,
        itemListElement: sessionItems,
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home",        item: BASE },
          { "@type": "ListItem", position: 2, name: "Past Papers", item: `${BASE}/past-papers` },
          { "@type": "ListItem", position: 3, name: subjectName,   item: pageUrl },
        ],
      },
    ],
  }
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default async function SubjectPapersPage({
  params,
}: {
  params: Promise<{ subject: string }>
}) {
  const { subject: slug } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) notFound()

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

  let papers: PaperRow[] = []

  if (subjectRow) {
    const { data } = await supabase
      .from("papers")
      .select("id, paper_number, year, season, pdf_url, markscheme_pdf_url")
      .eq("subject_id", subjectRow.id)
      .in("season", Array.from(VALID_SEASONS))
      .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
      .order("year", { ascending: false })
      .order("season", { ascending: false })

    papers = ((data as PaperRow[]) ?? [])
      .map((paper) => ({
        ...paper,
        season: normalizeSeason(paper.season),
        pdf_url: isValidPublicUrl(paper.pdf_url) ? paper.pdf_url : null,
        markscheme_pdf_url: isValidPublicUrl(paper.markscheme_pdf_url) ? paper.markscheme_pdf_url : null,
      }))
      .filter((paper) => VALID_SEASONS.has(paper.season))
      .filter((paper) => Boolean(paper.pdf_url) || Boolean(paper.markscheme_pdf_url))
  }

  // Group by year → season
  const yearMap = new Map<number, Map<string, PaperRow[]>>()
  for (const p of papers) {
    if (!yearMap.has(p.year)) yearMap.set(p.year, new Map())
    const sess = yearMap.get(p.year)!
    if (!sess.has(p.season)) sess.set(p.season, [])
    sess.get(p.season)!.push(p)
  }

  const yearGroups: YearGroup[] = Array.from(yearMap.entries())
    .sort(([a], [b]) => b - a)
    .map(([year, sessMap]) => ({
      year,
      sessions: Array.from(sessMap.entries())
        .sort(([a], [b]) => (SEASON_ORDER[a] ?? 9) - (SEASON_ORDER[b] ?? 9))
        .map(([season, sessionPapers]) => ({
          season,
          displaySeason: seasonDisplay(season),
          papers: dedupeSessionPapers(sessionPapers),
        })),
    }))
    .map((group) => ({
      ...group,
      sessions: group.sessions.filter((session) => session.papers.length > 0),
    }))
    .filter((group) => group.sessions.length > 0)

  const jsonLd = buildJsonLd(slug, subj.name, level, yearGroups)

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="min-h-screen bg-black text-white">
        {/* Sticky header */}
        <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
            <Link
              href="/past-papers"
              className="text-white/60 hover:text-white transition-colors text-sm"
            >
              ← Past Papers
            </Link>
            <span className="text-white/20">|</span>
            <h1 className="text-lg font-bold">{subj.name}</h1>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colorClass}`}>
              Edexcel {level}
            </span>
          </div>
        </div>

        <div className="max-w-5xl mx-auto px-6 py-10">
          {/* Page Title */}
          <div className="mb-10">
            <h2 className="text-3xl font-extrabold mb-2">{subj.name} Past Papers</h2>
            <p className="text-white/50">
              Download free Edexcel {level} {subj.name} question papers and mark schemes.
            </p>
          </div>

          {/* Empty State */}
          {yearGroups.length === 0 && (
            <div style={{ textAlign: "center", padding: "5rem 0", color: "#6B7280" }}>
              <p style={{ fontSize: "1rem", fontWeight: 600, color: "#9CA3AF", marginBottom: "0.5rem" }}>No papers available yet</p>
              <p style={{ fontSize: "0.85rem" }}>Papers for {subj.name} will be uploaded soon.</p>
            </div>
          )}

          {/* Year Groups */}
          <div className="space-y-6">
            {yearGroups.map((yg) => (
              <details
                key={yg.year}
                className="group bg-white/[0.03] border border-white/10 rounded-xl overflow-hidden"
                open={yg.year >= new Date().getFullYear() - 2}
              >
                <summary className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-white/[0.03] transition-colors select-none">
                  <span className="text-xl font-bold">{yg.year}</span>
                  <span className="text-white/30 text-sm group-open:rotate-180 transition-transform">▼</span>
                </summary>

                <div className="px-6 pb-5 space-y-6">
                  {yg.sessions.map((sess) => (
                    <div key={sess.season}>
                      {/* Session header with link to dedicated session page */}
                      <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
                          {sess.displaySeason}
                        </h3>
                        <Link
                          href={`/past-papers/${slug}/${yg.year}/${sess.season}`}
                          className="text-xs text-white/30 hover:text-white/60 transition-colors"
                        >
                          View session page →
                        </Link>
                      </div>

                      <div className="space-y-2">
                        {sess.papers.map((paper) => (
                          <div
                            key={paper.id}
                            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-white/[0.02] rounded-lg px-4 py-3 hover:bg-white/[0.05] transition-colors"
                          >
                            <span className="font-medium text-sm">Paper {paper.paper_number}</span>

                            <div className="flex gap-2 flex-wrap">
                              {paper.pdf_url ? (
                                <a
                                  href={paper.pdf_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
                                             bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30
                                             hover:bg-blue-500/25 transition-colors"
                                >
                                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round"
                                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                  </svg>
                                  <span className="hidden sm:inline">Question Paper</span>
                                  <span className="sm:hidden">QP</span>
                                </a>
                              ) : (
                                <span className="inline-flex items-center px-3 py-1.5 text-xs rounded-lg text-white/20">QP —</span>
                              )}

                              {paper.markscheme_pdf_url ? (
                                <a
                                  href={paper.markscheme_pdf_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
                                             bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30
                                             hover:bg-emerald-500/25 transition-colors"
                                >
                                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round"
                                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  <span className="hidden sm:inline">Mark Scheme</span>
                                  <span className="sm:hidden">MS</span>
                                </a>
                              ) : (
                                <span className="inline-flex items-center px-3 py-1.5 text-xs rounded-lg text-white/20">MS —</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </div>
      </main>
    </>
  )
}
