import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import {
  pastPaperSubjects,
  getSubjectBySlug,
  subjectColorClasses,
  seasonDisplay,
} from "@/lib/subjects"
import { seoSubjects } from "@/lib/seo-subjects"

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
  const seoData = seoSubjects.find(s => s.slug === slug)
  const examCode = seoData?.examCode ?? ''
  const codeStr = examCode ? ` (${examCode})` : ''

  return {
    title: `Edexcel ${level} ${subj.name}${codeStr} Past Papers – Free Download | GradeMax`,
    description: `Download free Edexcel ${level} ${subj.name}${codeStr} past papers and mark schemes from 2011 to 2025. All question papers organised by year and session – free PDF download.`,
    keywords: [
      `${subj.name} past papers`,
      `${level} ${subj.name} past papers`,
      `Edexcel ${subj.name} past papers`,
      `${subj.name} question papers`,
      `${subj.name} mark scheme`,
      `${subj.name} past papers free download`,
      ...(examCode ? [
        `${examCode} past papers`,
        `${examCode} question papers`,
        `${examCode} mark scheme`,
        `Edexcel ${examCode}`,
      ] : []),
      `Edexcel ${level} ${subj.name}`,
      `${subj.name} past papers 2025`,
      `${subj.name} past papers 2024`,
      `${subj.name} past papers 2023`,
      `free ${subj.name} past papers`,
    ],
    openGraph: {
      title: `Edexcel ${level} ${subj.name}${codeStr} Past Papers – Free Download | GradeMax`,
      description: `Download free Edexcel ${level} ${subj.name}${codeStr} past papers and mark schemes from 2011 to 2025. All sessions available as free PDF.`,
      url: `https://grademax.me/past-papers/${slug}`,
      siteName: "GradeMax",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${level} ${subj.name}${codeStr} Past Papers | GradeMax`,
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

      <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
        {/* Header */}
        <div style={{ borderBottom: "1px solid var(--gm-border)", background: "var(--gm-nav-bg)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", position: "sticky", top: "68px", zIndex: 10 }}>
          <div style={{ maxWidth: "900px", margin: "0 auto", padding: "0.875rem 1.5rem", display: "flex", alignItems: "center", gap: "0.875rem", flexWrap: "wrap" }}>
            <Link href="/past-papers" className="gm-link" style={{ fontSize: "0.82rem" }}>
              ← Past Papers
            </Link>
            <span style={{ color: "var(--gm-border-2)" }}>|</span>
            <h1 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--gm-text)", margin: 0 }}>{subj.name}</h1>
            <span style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em", padding: "0.2rem 0.625rem", borderRadius: "99px", background: "var(--gm-blue-bg)", color: "var(--gm-blue)", border: "1px solid var(--gm-blue-ring)" }}>
              Edexcel {level}
            </span>
          </div>
        </div>

        <div style={{ maxWidth: "900px", margin: "0 auto", padding: "2.5rem 1.5rem" }}>
          {/* Page Title */}
          <div style={{ marginBottom: "2.5rem" }}>
            <h2 style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.5rem" }}>
              {subj.name} Past Papers
            </h2>
            <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>
              Free Edexcel {level} {subj.name} question papers and mark schemes.
            </p>
          </div>

          {/* Empty State */}
          {yearGroups.length === 0 && (
            <div style={{ textAlign: "center", padding: "5rem 0", color: "var(--gm-text-3)" }}>
              <p style={{ fontSize: "1rem", fontWeight: 600, color: "var(--gm-text-2)", marginBottom: "0.5rem" }}>No papers available yet</p>
              <p style={{ fontSize: "0.85rem" }}>Papers for {subj.name} will be uploaded soon.</p>
            </div>
          )}

          {/* Year Groups */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {yearGroups.map((yg) => (
              <details
                key={yg.year}
                style={{ background: "var(--gm-card-bg)", border: "1px solid var(--gm-border-2)", borderRadius: "1rem", overflow: "hidden" }}
                open={yg.year >= new Date().getFullYear() - 2}
              >
                <summary style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "1rem 1.25rem", cursor: "pointer", userSelect: "none", listStyle: "none" }}>
                  <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gm-text)" }}>{yg.year}</span>
                  <span style={{ color: "var(--gm-text-3)", fontSize: "0.75rem" }}>▼</span>
                </summary>

                <div style={{ padding: "0 1.25rem 1.25rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                  {yg.sessions.map((sess) => (
                    <div key={sess.season}>
                      {/* Session header */}
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--gm-border)", paddingBottom: "0.5rem", marginBottom: "0.75rem" }}>
                        <h3 style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-text-2)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                          {sess.displaySeason}
                        </h3>
                        <Link
                          href={`/past-papers/${slug}/${yg.year}/${sess.season}`}
                          className="gm-link"
                          style={{ fontSize: "0.72rem" }}
                        >
                          Session page →
                        </Link>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                        {sess.papers.map((paper) => (
                          <div
                            key={paper.id}
                            style={{
                              display: "flex",
                              flexWrap: "wrap",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "0.5rem",
                              background: "var(--gm-surface)",
                              borderRadius: "0.625rem",
                              padding: "0.75rem 1rem",
                              border: "1px solid var(--gm-border)",
                            }}
                          >
                            <span style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--gm-text)" }}>Paper {paper.paper_number}</span>

                            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                              {paper.pdf_url ? (
                                <a
                                  href={paper.pdf_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "0.35rem",
                                    padding: "0.35rem 0.75rem",
                                    fontSize: "0.75rem",
                                    fontWeight: 600,
                                    borderRadius: "0.5rem",
                                    background: "var(--gm-blue-bg)",
                                    color: "var(--gm-blue)",
                                    border: "1px solid var(--gm-blue-ring)",
                                    textDecoration: "none",
                                    transition: "background 0.15s",
                                  }}
                                >
                                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                  </svg>
                                  Question Paper
                                </a>
                              ) : (
                                <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", padding: "0.35rem 0.75rem" }}>QP —</span>
                              )}

                              {paper.markscheme_pdf_url ? (
                                <a
                                  href={paper.markscheme_pdf_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "0.35rem",
                                    padding: "0.35rem 0.75rem",
                                    fontSize: "0.75rem",
                                    fontWeight: 600,
                                    borderRadius: "0.5rem",
                                    background: "var(--gm-green-bg)",
                                    color: "var(--gm-green)",
                                    border: "1px solid rgba(52,211,153,0.25)",
                                    textDecoration: "none",
                                    transition: "background 0.15s",
                                  }}
                                >
                                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  Mark Scheme
                                </a>
                              ) : (
                                <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", padding: "0.35rem 0.75rem" }}>MS —</span>
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
