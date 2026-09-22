import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import {
  pastPaperSubjects,
  getSubjectBySlug,
  seasonDisplay,
  boardOf,
  boardDisplay,
  levelShort,
  catalogHref,
  dbNameOf,
} from "@/lib/subjects"
import { seoSubjects, isSingleUnitEdexcelCode } from "@/lib/seo-subjects"
import { toPaperSlug, formatPaperLabel, formatCambridgePaperLabel, cambridgePaperCode, comparePaperNumbers } from "@/lib/paper-slugs"
import PaperRow from "@/components/past-papers/PaperRow"

// Subject hub pages are pre-rendered at build time and stay static until the
// next deploy. New papers added between deploys are picked up on the next push.
export const revalidate = false

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

  const level = levelShort(subj.level)
  const board = boardDisplay(subj.level)
  const yearRange = boardOf(subj.level) === "cambridge" ? "2015 to 2025" : "2011 to 2025"
  const seoData = seoSubjects.find(s => s.slug === slug)
  const examCode = seoData?.examCode ?? subj.examCode ?? ''
  const codeStr = examCode ? ` (${examCode})` : ''
  const codeLed = isSingleUnitEdexcelCode(examCode) && !subj.name.startsWith('IAL ')
  // Lead with the code for code-searched subjects. The /past-papers layout sets a
  // plain-string title, which blocks the root "%s | GradeMax" template from this
  // subtree, so the brand suffix must be included explicitly.
  const title = codeLed
    ? `${examCode} Past Papers – Edexcel ${level} ${subj.name} Mark Schemes`
    : `${board} ${level} ${subj.name}${codeStr} Past Papers – Free PDF with Mark Schemes`

  return {
    title: `${title} | GradeMax`,
    description: `Download free ${board} ${level} ${subj.name}${codeStr} past papers and mark schemes from ${yearRange}. All question papers organised by year and session – free PDF download.`,
    keywords: [
      `${subj.name} past papers`,
      `${level} ${subj.name} past papers`,
      `${board} ${subj.name} past papers`,
      `${subj.name} question papers`,
      `${subj.name} mark scheme`,
      `${subj.name} past papers free download`,
      ...(examCode ? [
        `${examCode} past papers`,
        `${examCode} question papers`,
        `${examCode} mark scheme`,
        `${board} ${examCode}`,
      ] : []),
      `${board} ${level} ${subj.name}`,
      `${subj.name} past papers 2025`,
      `${subj.name} past papers 2024`,
      `${subj.name} past papers 2023`,
      `free ${subj.name} past papers`,
    ],
    openGraph: {
      title: `${title} | GradeMax`,
      description: `Download free ${board} ${level} ${subj.name}${codeStr} past papers and mark schemes from ${yearRange}. All sessions available as free PDF.`,
      url: `https://www.grademax.me/past-papers/${slug}`,
      siteName: "GradeMax",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${level} ${subj.name}${codeStr} Past Papers | GradeMax`,
      description: `Free ${board} ${level} ${subj.name} past papers with mark schemes.`,
    },
    alternates: {
      canonical: `https://www.grademax.me/past-papers/${slug}`,
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
  data_file_url: string | null
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

    const score = (p: PaperRow) =>
      Number(Boolean(p.pdf_url)) +
      Number(Boolean(p.markscheme_pdf_url)) +
      Number(Boolean(p.data_file_url))

    const existingScore = score(existing)
    const paperScore = score(paper)

    if (paperScore > existingScore || (paperScore === existingScore && paper.id > existing.id)) {
      byPaperNumber.set(paper.paper_number, paper)
    }
  }

  return Array.from(byPaperNumber.values()).sort((a, b) => comparePaperNumbers(a.paper_number, b.paper_number))
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

const SEASON_ORDER: Record<string, number> = {
  jan: 0, "jan-feb": 0, "feb-mar": 1, "may-jun": 2, "oct-nov": 3,
}

// ─── JSON-LD ───────────────────────────────────────────────────────────────────

function buildJsonLd(slug: string, subjectName: string, level: string, board: string, catalogPath: string, yearGroups: YearGroup[]) {
  const BASE = "https://www.grademax.me"
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
        name: `${board} ${level} ${subjectName} Past Papers`,
        description: `Free ${board} ${level} ${subjectName} past papers and mark schemes, organised by year and session.`,
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
          educationalFramework: board,
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
          { "@type": "ListItem", position: 2, name: `${board} Past Papers`, item: `${BASE}${catalogPath}` },
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

  const level = levelShort(subj.level)
  const board = boardDisplay(subj.level)
  const catalogPath = catalogHref(subj.level)
  const isEdexcel = boardOf(subj.level) === "edexcel"

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )

  // Use ilike + ordering instead of strict eq so we tolerate duplicate subject
  // rows (e.g. legacy "International GCSE" + new "IGCSE" with the same name).
  // Cambridge subjects store a board-prefixed name in the DB (dbNameOf).
  const { data: subjectRows } = await supabase
    .from("subjects")
    .select("id")
    .ilike("name", dbNameOf(subj))

  const subjectIds = (subjectRows ?? []).map((r) => r.id)

  let papers: PaperRow[] = []

  if (subjectIds.length > 0) {
    const selectCols = "id, paper_number, year, season, pdf_url, markscheme_pdf_url, data_file_url"
    const initial = await supabase
      .from("papers")
      .select(selectCols)
      .in("subject_id", subjectIds)
      .in("season", Array.from(VALID_SEASONS))
      .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
      .order("year", { ascending: false })
      .order("season", { ascending: false })

    // Fallback for environments where `data_file_url` hasn't been added yet.
    let data: PaperRow[] | null = (initial.data as unknown as PaperRow[]) ?? null
    if (initial.error?.code === "42703") {
      const fallback = await supabase
        .from("papers")
        .select("id, paper_number, year, season, pdf_url, markscheme_pdf_url")
        .in("subject_id", subjectIds)
        .in("season", Array.from(VALID_SEASONS))
        .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
        .order("year", { ascending: false })
        .order("season", { ascending: false })
      data = (fallback.data as unknown as PaperRow[]) ?? null
    }

    papers = ((data as PaperRow[]) ?? [])
      .map((paper) => ({
        ...paper,
        season: normalizeSeason(paper.season),
        pdf_url: isValidPublicUrl(paper.pdf_url) ? paper.pdf_url : null,
        markscheme_pdf_url: isValidPublicUrl(paper.markscheme_pdf_url) ? paper.markscheme_pdf_url : null,
        data_file_url: isValidPublicUrl(paper.data_file_url ?? null) ? paper.data_file_url : null,
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

  // Which year accordions start expanded. Anchored to the subject's own newest
  // year, not to the wall-clock year: subjects whose archive stops earlier (IAL
  // French ends at 2022, Mechanics 1 at 2019) previously rendered every group
  // collapsed, so the page looked empty even though the papers were all there.
  const newestYear = yearGroups[0]?.year ?? 0
  const firstOpenYear = newestYear - 1

  const jsonLd = buildJsonLd(slug, subj.name, level, board, catalogPath, yearGroups)

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
            <Link href={catalogPath} className="gm-link" style={{ fontSize: "0.82rem" }}>
              ← Past Papers
            </Link>
            <span style={{ color: "var(--gm-border-2)" }}>|</span>
            <h1 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--gm-text)", margin: 0 }}>{subj.name}</h1>
            <span style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em", padding: "0.2rem 0.625rem", borderRadius: "99px", background: "var(--gm-blue-bg)", color: "var(--gm-blue)", border: "1px solid var(--gm-blue-ring)" }}>
              {board} {level}
            </span>
            {!isEdexcel && subj.examCode && (
              <span style={{ fontSize: "0.6rem", fontWeight: 700, fontFamily: "monospace", letterSpacing: "0.04em", padding: "0.2rem 0.5rem", borderRadius: "5px", background: "var(--gm-card-bg)", color: "var(--gm-text-2)", border: "1px solid var(--gm-border-2)" }}>
                {subj.examCode}
              </span>
            )}
          </div>
        </div>

        <div style={{ maxWidth: "900px", margin: "0 auto", padding: "2.5rem 1.5rem" }}>
          {/* Page Title */}
          <div style={{ marginBottom: "2.5rem" }}>
            <h2 style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.5rem" }}>
              {subj.name} Past Papers
            </h2>
            <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>
              Free {board} {level} {subj.name}{!isEdexcel && subj.examCode ? ` (${subj.examCode})` : ""} question papers and mark schemes.
              {!isEdexcel && " Papers are labelled by component and variant (e.g. Paper 2 · Variant 2 = 22)."}
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
                open={yg.year >= firstOpenYear}
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

                      <div>
                        {sess.papers.map((paper) => {
                          // Use the canonical slug helper so it matches the static-build paths
                          // (the index keys leaves with toPaperSlug, which normalises `_` and spaces to `-`).
                          const paperPageSlug = toPaperSlug(paper.paper_number)
                          if (!paperPageSlug) return null
                          const paperLabel = isEdexcel ? formatPaperLabel(paper.paper_number) : formatCambridgePaperLabel(paper.paper_number)
                          const paperCode = isEdexcel ? "" : cambridgePaperCode(subj.examCode, paper.paper_number)
                          return (
                            <PaperRow
                              key={paper.id}
                              id={`${yg.year}-${sess.season}-${paperPageSlug}`}
                              href={`/past-papers/${slug}/${yg.year}/${sess.season}/${paperPageSlug}`}
                              label={paperLabel}
                              code={paperCode}
                              qpUrl={paper.pdf_url}
                              msUrl={paper.markscheme_pdf_url}
                              dataUrl={paper.data_file_url}
                              viewerTitle={`${subj.name} ${yg.year} ${sess.displaySeason} ${paperLabel}`}
                              backPath={`/past-papers/${slug}`}
                            />
                          )
                        })}
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
