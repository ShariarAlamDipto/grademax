import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import { getSubjectBySlug, seasonDisplay } from "@/lib/subjects"
import { seoSubjects } from "@/lib/seo-subjects"

// ─── Types ────────────────────────────────────────────────────────────────────

interface PaperRow {
  id: string
  year: number
  season: string
  pdf_url: string | null
  markscheme_pdf_url: string | null
}

interface SessionEntry {
  season: string
  displaySeason: string
  paper: PaperRow
}

interface YearEntry {
  year: number
  sessions: SessionEntry[]
}

// ─── Constants ────────────────────────────────────────────────────────────────

const VALID_SEASONS = new Set(["jan", "jan-feb", "feb-mar", "may-jun", "oct-nov"])

const SEASON_ORDER: Record<string, number> = {
  jan: 0,
  "jan-feb": 0,
  "feb-mar": 1,
  "may-jun": 2,
  "oct-nov": 3,
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isValidPublicUrl(url: string | null): url is string {
  if (!url) return false
  return /^https?:\/\//i.test(url)
}

// ─── Component ────────────────────────────────────────────────────────────────

export interface PaperHubPageProps {
  subject: string
  paperNumber: string
}

export async function PaperHubPage({ subject: slug, paperNumber }: PaperHubPageProps) {
  const subj = getSubjectBySlug(slug)
  if (!subj) notFound()

  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const seoData = seoSubjects.find((s) => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const codeStr = examCode ? ` (${examCode})` : ""
  const paperSlug = `paper-${paperNumber.toLowerCase()}`

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
      .select("id, year, season, pdf_url, markscheme_pdf_url")
      .eq("subject_id", subjectRow.id)
      .eq("paper_number", paperNumber)
      .in("season", Array.from(VALID_SEASONS))
      .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
      .order("year", { ascending: false })

    papers = ((data as PaperRow[]) ?? [])
      .map((p) => ({
        ...p,
        season: p.season.trim().toLowerCase(),
        pdf_url: isValidPublicUrl(p.pdf_url) ? p.pdf_url : null,
        markscheme_pdf_url: isValidPublicUrl(p.markscheme_pdf_url) ? p.markscheme_pdf_url : null,
      }))
      .filter((p) => VALID_SEASONS.has(p.season))
      .filter((p) => Boolean(p.pdf_url) || Boolean(p.markscheme_pdf_url))
  }

  // Group by year → sort by season within each year
  const yearMap = new Map<number, PaperRow[]>()
  for (const p of papers) {
    if (!yearMap.has(p.year)) yearMap.set(p.year, [])
    yearMap.get(p.year)!.push(p)
  }

  const yearEntries: YearEntry[] = Array.from(yearMap.entries())
    .sort(([a], [b]) => b - a)
    .map(([year, sessionPapers]) => ({
      year,
      sessions: sessionPapers
        .sort((a, b) => (SEASON_ORDER[a.season] ?? 9) - (SEASON_ORDER[b.season] ?? 9))
        .map((p) => ({
          season: p.season,
          displaySeason: seasonDisplay(p.season),
          paper: p,
        })),
    }))
    .filter((yg) => yg.sessions.length > 0)

  // JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "LearningResource",
        "@id": `https://grademax.me/past-papers/${slug}/${paperSlug}#resource`,
        name: `Edexcel ${level} ${subj.name}${codeStr} Paper ${paperNumber} Past Papers`,
        description: `All Edexcel ${level} ${subj.name}${codeStr} Paper ${paperNumber} past papers and mark schemes from 2011 to 2025, organised by year and session.`,
        url: `https://grademax.me/past-papers/${slug}/${paperSlug}`,
        isAccessibleForFree: true,
        inLanguage: "en-GB",
        educationalLevel: level,
        learningResourceType: ["Past Paper", "Examination"],
        provider: { "@type": "Organization", name: "GradeMax", url: "https://grademax.me" },
        educationalAlignment: {
          "@type": "AlignmentObject",
          alignmentType: "educationalSubject",
          targetName: subj.name,
          educationalFramework: "Edexcel",
        },
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: "https://grademax.me" },
          { "@type": "ListItem", position: 2, name: "Past Papers", item: "https://grademax.me/past-papers" },
          { "@type": "ListItem", position: 3, name: subj.name, item: `https://grademax.me/past-papers/${slug}` },
          { "@type": "ListItem", position: 4, name: `Paper ${paperNumber}`, item: `https://grademax.me/past-papers/${slug}/${paperSlug}` },
        ],
      },
      {
        "@type": "ItemList",
        name: `${subj.name} Paper ${paperNumber} – All Years`,
        numberOfItems: yearEntries.length,
        itemListElement: yearEntries.map((yg, i) => ({
          "@type": "ListItem",
          position: i + 1,
          name: `${subj.name} ${yg.year} Paper ${paperNumber}`,
          url: `https://grademax.me/past-papers/${slug}/${yg.year}`,
        })),
      },
    ],
  }

  const otherPapers = ["1", "2", "3", "4"].filter((n) => n !== paperNumber)

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
        {/* Sticky breadcrumb nav */}
        <div
          style={{
            borderBottom: "1px solid var(--gm-border)",
            background: "var(--gm-nav-bg)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            position: "sticky",
            top: "68px",
            zIndex: 10,
          }}
        >
          <div
            style={{
              maxWidth: "900px",
              margin: "0 auto",
              padding: "0.875rem 1.5rem",
              display: "flex",
              alignItems: "center",
              gap: "0.625rem",
              flexWrap: "wrap",
            }}
          >
            <Link href="/past-papers" className="gm-link" style={{ fontSize: "0.82rem" }}>
              Past Papers
            </Link>
            <span style={{ color: "var(--gm-text-3)", fontSize: "0.75rem" }}>›</span>
            <Link href={`/past-papers/${slug}`} className="gm-link" style={{ fontSize: "0.82rem" }}>
              {subj.name}
            </Link>
            <span style={{ color: "var(--gm-text-3)", fontSize: "0.75rem" }}>›</span>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gm-text)" }}>
              Paper {paperNumber}
            </span>
            <span
              style={{
                fontSize: "0.6rem",
                fontWeight: 700,
                letterSpacing: "0.08em",
                padding: "0.2rem 0.625rem",
                borderRadius: "99px",
                background: "var(--gm-blue-bg)",
                color: "var(--gm-blue)",
                border: "1px solid var(--gm-blue-ring)",
              }}
            >
              Edexcel {level}
            </span>
          </div>
        </div>

        <div style={{ maxWidth: "900px", margin: "0 auto", padding: "2.5rem 1.5rem" }}>
          {/* Page header */}
          <div style={{ marginBottom: "2.5rem" }}>
            <p
              style={{
                fontSize: "0.7rem",
                fontWeight: 700,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--gm-amber)",
                marginBottom: "0.5rem",
              }}
            >
              Edexcel {level} · {subj.name}{codeStr}
            </p>
            <h1
              style={{
                fontSize: "clamp(1.6rem, 4vw, 2.2rem)",
                fontWeight: 800,
                color: "var(--gm-text)",
                letterSpacing: "-0.02em",
                lineHeight: 1.1,
                marginBottom: "0.625rem",
              }}
            >
              Paper {paperNumber} Past Papers
            </h1>
            <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem", lineHeight: 1.6, maxWidth: "520px" }}>
              All {subj.name} Paper {paperNumber} question papers and mark schemes across every year and session — free PDF download.
            </p>

            {/* Paper switcher pills */}
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1.25rem" }}>
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  padding: "0.3rem 0.875rem",
                  borderRadius: "99px",
                  background: "var(--gm-blue-bg)",
                  color: "var(--gm-blue)",
                  border: "1px solid var(--gm-blue-ring)",
                }}
              >
                Paper {paperNumber}
              </span>
              {otherPapers.map((n) => (
                <Link
                  key={n}
                  href={`/past-papers/${slug}/paper-${n}`}
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    padding: "0.3rem 0.875rem",
                    borderRadius: "99px",
                    background: "transparent",
                    color: "var(--gm-text-2)",
                    border: "1px solid var(--gm-border-2)",
                    textDecoration: "none",
                    transition: "border-color 0.15s, color 0.15s",
                  }}
                >
                  Paper {n}
                </Link>
              ))}
            </div>
          </div>

          {/* Empty state */}
          {yearEntries.length === 0 && (
            <div style={{ textAlign: "center", padding: "5rem 0", color: "var(--gm-text-3)" }}>
              <p
                style={{
                  fontSize: "1rem",
                  fontWeight: 600,
                  color: "var(--gm-text-2)",
                  marginBottom: "0.5rem",
                }}
              >
                No papers found
              </p>
              <p style={{ fontSize: "0.85rem" }}>
                No Paper {paperNumber} entries are available for {subj.name} yet.
              </p>
              <Link
                href={`/past-papers/${slug}`}
                className="btn-ghost-blue"
                style={{ display: "inline-block", marginTop: "1.5rem", fontSize: "0.8rem" }}
              >
                ← Back to all {subj.name} papers
              </Link>
            </div>
          )}

          {/* Year rows */}
          {yearEntries.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {yearEntries.map((yg) => (
                <div
                  key={yg.year}
                  style={{
                    background: "var(--gm-card-bg)",
                    border: "1px solid var(--gm-border-2)",
                    borderRadius: "0.875rem",
                    overflow: "hidden",
                  }}
                >
                  {/* Year header */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "0.875rem 1.25rem",
                      borderBottom: "1px solid var(--gm-border)",
                    }}
                  >
                    <span style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--gm-text)" }}>
                      {yg.year}
                    </span>
                    <Link
                      href={`/past-papers/${slug}/${yg.year}`}
                      className="gm-link"
                      style={{ fontSize: "0.72rem" }}
                    >
                      All {yg.year} papers →
                    </Link>
                  </div>

                  {/* Sessions */}
                  <div
                    style={{
                      padding: "0.75rem 1.25rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.4rem",
                    }}
                  >
                    {yg.sessions.map(({ season, displaySeason, paper }) => (
                      <div
                        key={season}
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
                        <Link
                          href={`/past-papers/${slug}/${yg.year}/${season}/${paperSlug}`}
                          className="gm-link"
                          style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--gm-text)" }}
                        >
                          {displaySeason}
                        </Link>

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
                              }}
                            >
                              <svg
                                width="12"
                                height="12"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                />
                              </svg>
                              Question Paper
                            </a>
                          ) : (
                            <span
                              style={{
                                fontSize: "0.75rem",
                                color: "var(--gm-text-3)",
                                padding: "0.35rem 0.75rem",
                              }}
                            >
                              QP —
                            </span>
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
                              }}
                            >
                              <svg
                                width="12"
                                height="12"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                              </svg>
                              Mark Scheme
                            </a>
                          ) : (
                            <span
                              style={{
                                fontSize: "0.75rem",
                                color: "var(--gm-text-3)",
                                padding: "0.35rem 0.75rem",
                              }}
                            >
                              MS —
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer bar */}
          {yearEntries.length > 0 && (
            <div
              style={{
                marginTop: "2.5rem",
                borderTop: "1px solid var(--gm-border)",
                paddingTop: "1.5rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "1rem",
              }}
            >
              <Link href={`/past-papers/${slug}`} className="gm-link" style={{ fontSize: "0.8rem" }}>
                ← All {subj.name} papers by year
              </Link>
              <Link href="/past-papers" className="gm-link" style={{ fontSize: "0.8rem" }}>
                Browse all subjects
              </Link>
            </div>
          )}
        </div>
      </main>
    </>
  )
}

// ─── Metadata builder (shared across all paper-N pages) ───────────────────────

export async function buildPaperHubMetadata(slug: string, paperNumber: string) {
  const subj = getSubjectBySlug(slug)
  if (!subj) return {}

  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const seoData = seoSubjects.find((s) => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const codeStr = examCode ? ` (${examCode})` : ""
  const paperSlug = `paper-${paperNumber}`

  return {
    title: `Edexcel ${level} ${subj.name}${codeStr} Paper ${paperNumber} Past Papers – All Years | GradeMax`,
    description: `Download all free Edexcel ${level} ${subj.name}${codeStr} Paper ${paperNumber} past papers with mark schemes from 2011 to 2025. Every year and session in one place.`,
    keywords: [
      `${subj.name} Paper ${paperNumber} past papers`,
      `${level} ${subj.name} Paper ${paperNumber}`,
      `Edexcel ${subj.name} Paper ${paperNumber}`,
      `${subj.name} Paper ${paperNumber} all years`,
      `${subj.name} Paper ${paperNumber} mark scheme`,
      ...(examCode
        ? [`${examCode} Paper ${paperNumber}`, `${examCode} Paper ${paperNumber} past papers`]
        : []),
      `${subj.name} Paper ${paperNumber} 2025`,
      `${subj.name} Paper ${paperNumber} 2024`,
      `${subj.name} Paper ${paperNumber} 2023`,
    ],
    openGraph: {
      title: `Edexcel ${level} ${subj.name} Paper ${paperNumber} Past Papers – All Years | GradeMax`,
      description: `All ${subj.name} Paper ${paperNumber} question papers and mark schemes, every year and session. Free PDF download.`,
      url: `https://grademax.me/past-papers/${slug}/${paperSlug}`,
      siteName: "GradeMax",
      type: "website" as const,
    },
    twitter: {
      card: "summary_large_image" as const,
      title: `${level} ${subj.name} Paper ${paperNumber} Past Papers | GradeMax`,
      description: `All Edexcel ${level} ${subj.name} Paper ${paperNumber} past papers with mark schemes.`,
    },
    alternates: {
      canonical: `https://grademax.me/past-papers/${slug}/${paperSlug}`,
    },
  }
}
