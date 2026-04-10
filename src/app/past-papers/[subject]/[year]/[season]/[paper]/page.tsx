import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import { getSubjectBySlug, subjectColorClasses, seasonDisplay } from "@/lib/subjects"
import { seoSubjects } from "@/lib/seo-subjects"
import { extractPaperTokenFromSlug, normalizePaperToken, toPaperSlug } from "@/lib/paper-slugs"

export const revalidate = 3600

function parseYearParam(value: string): number | null {
  if (!/^\d{4}$/.test(value)) return null
  const year = Number.parseInt(value, 10)
  if (year < 2000 || year > 2100) return null
  return year
}

// Pre-render popular paper combos for fast initial indexing.
// ISR handles everything else on-demand.
export function generateStaticParams() {
  const popularSubjects = [
    "physics", "chemistry", "biology", "maths-a", "maths-b",
    "pure-mathematics-1", "mechanics-1", "statistics-1",
  ]
  const recentYears = ["2025", "2024", "2023", "2022"]
  const mainSeasons = ["may-jun", "oct-nov", "jan"]
  const commonPapers = ["paper-1", "paper-2", "paper-1r", "paper-2r"]
  const params: { subject: string; year: string; season: string; paper: string }[] = []

  for (const subject of popularSubjects) {
    for (const year of recentYears) {
      for (const season of mainSeasons) {
        for (const paper of commonPapers) {
          params.push({ subject, year, season, paper })
        }
      }
    }
  }
  return params
}

// ─── Metadata ──────────────────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subject: string; year: string; season: string; paper: string }>
}) {
  const { subject: slug, year, season, paper: paperSlug } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) return {}
  const parsedYear = parseYearParam(year)
  if (parsedYear === null) return {}
  const yearLabel = String(parsedYear)
  const normalizedSeason = normalizeSeason(season)
  if (!VALID_SEASONS.has(normalizedSeason)) return {}

  const paperToken = extractPaperTokenFromSlug(paperSlug)
  if (!paperToken) return {}
  const normalizedPaperSlug = toPaperSlug(paperToken)
  if (!normalizedPaperSlug) return {}

  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const seasonName = seasonDisplay(normalizedSeason)
  const seoData = seoSubjects.find(s => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const codeStr = examCode ? ` (${examCode})` : ""
  const displayPaper = `Paper ${paperToken.toUpperCase().replace(/-/g, " ")}`

  return {
    title: `Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} ${displayPaper} – Free PDF | GradeMax`,
    description: `Download free Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} ${displayPaper} question paper and mark scheme as PDF. Official Pearson Edexcel past paper.`,
    keywords: [
      `${subj.name} ${yearLabel} ${seasonName} ${displayPaper}`,
      `${subj.name} ${yearLabel} paper ${paperToken}`,
      `Edexcel ${level} ${subj.name} ${yearLabel} ${seasonName} ${displayPaper}`,
      `${subj.name} ${yearLabel} ${seasonName} paper ${paperToken} question paper`,
      `${subj.name} ${yearLabel} ${seasonName} paper ${paperToken} mark scheme`,
      `${subj.name} ${yearLabel} paper ${paperToken} free download`,
      `${subj.name} ${yearLabel} paper ${paperToken} PDF`,
      ...(examCode
        ? [
            `${examCode} ${yearLabel} ${seasonName} paper ${paperToken}`,
            `${examCode} ${yearLabel} paper ${paperToken}`,
            `${examCode} paper ${paperToken} mark scheme ${yearLabel}`,
          ]
        : []),
      `Edexcel ${level} ${subj.name} ${yearLabel} ${displayPaper}`,
      `${level} ${subj.name} ${yearLabel} ${seasonName} ${displayPaper}`,
    ],
    openGraph: {
      title: `${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} ${displayPaper} | GradeMax`,
      description: `Free Edexcel ${level} ${subj.name} ${yearLabel} ${seasonName} ${displayPaper} question paper and mark scheme – PDF download.`,
      url: `https://grademax.me/past-papers/${slug}/${yearLabel}/${normalizedSeason}/${normalizedPaperSlug}`,
      siteName: "GradeMax",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} ${displayPaper} | GradeMax`,
      description: `Free download: ${subj.name} ${yearLabel} ${seasonName} ${displayPaper} QP & mark scheme.`,
    },
    alternates: {
      canonical: `https://grademax.me/past-papers/${slug}/${yearLabel}/${normalizedSeason}/${normalizedPaperSlug}`,
    },
  }
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface PaperRow {
  id: string
  paper_number: string
  pdf_url: string | null
  markscheme_pdf_url: string | null
}

const VALID_SEASONS = new Set(["jan", "jan-feb", "feb-mar", "may-jun", "oct-nov"])

function normalizeSeason(value: string): string {
  return value.trim().toLowerCase()
}

function isValidPublicUrl(url: string | null): url is string {
  if (!url) return false
  return /^https?:\/\//i.test(url)
}

// ─── JSON-LD ──────────────────────────────────────────────────────────────────

function buildJsonLd(
  slug: string,
  subjectName: string,
  level: string,
  year: string,
  season: string,
  seasonName: string,
  paperNumber: string,
  paper: PaperRow,
  examCode: string
) {
  const BASE = "https://grademax.me"
  const paperSlug = toPaperSlug(paperNumber) ?? `paper-${normalizePaperToken(paperNumber)}`
  const pageUrl = `${BASE}/past-papers/${slug}/${year}/${season}/${paperSlug}`
  const sessionUrl = `${BASE}/past-papers/${slug}/${year}/${season}`
  const displayPaper = `Paper ${paperNumber}`

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "LearningResource",
        "@id": `${pageUrl}#resource`,
        name: `Edexcel ${level} ${subjectName} ${year} ${seasonName} ${displayPaper}`,
        description: `Free Edexcel ${level} ${subjectName} ${year} ${seasonName} ${displayPaper} question paper and mark scheme.`,
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
        datePublished: `${year}-01-01`,
        alternativeHeadline: examCode
          ? `${examCode} ${year} ${seasonName} ${displayPaper}`
          : undefined,
        audience: {
          "@type": "EducationalAudience",
          educationalRole: "student",
          audienceType: `${level} students`,
        },
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          availability: "https://schema.org/InStock",
        },
        isPartOf: {
          "@type": "LearningResource",
          name: `Edexcel ${level} ${subjectName} ${year} ${seasonName} Past Papers`,
          url: sessionUrl,
        },
        hasPart: [
          ...(paper.pdf_url
            ? [
                {
                  "@type": "MediaObject",
                  name: `${subjectName} ${year} ${seasonName} ${displayPaper} Question Paper`,
                  encodingFormat: "application/pdf",
                  contentUrl: paper.pdf_url,
                },
              ]
            : []),
          ...(paper.markscheme_pdf_url
            ? [
                {
                  "@type": "MediaObject",
                  name: `${subjectName} ${year} ${seasonName} ${displayPaper} Mark Scheme`,
                  encodingFormat: "application/pdf",
                  contentUrl: paper.markscheme_pdf_url,
                },
              ]
            : []),
        ],
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home",                     item: BASE },
          { "@type": "ListItem", position: 2, name: "Past Papers",              item: `${BASE}/past-papers` },
          { "@type": "ListItem", position: 3, name: subjectName,                item: `${BASE}/past-papers/${slug}` },
          { "@type": "ListItem", position: 4, name: `${year} ${seasonName}`,    item: sessionUrl },
          { "@type": "ListItem", position: 5, name: displayPaper,               item: pageUrl },
        ],
      },
    ],
  }
}

function serializeJsonLd(schema: object): string {
  return JSON.stringify(schema).replace(/</g, "\\u003c")
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function PaperPage({
  params,
}: {
  params: Promise<{ subject: string; year: string; season: string; paper: string }>
}) {
  const { subject: slug, year, season, paper: paperSlug } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) notFound()
  const parsedYear = parseYearParam(year)
  if (parsedYear === null) notFound()
  const yearLabel = String(parsedYear)

  const paperToken = extractPaperTokenFromSlug(paperSlug)
  if (!paperToken) notFound()

  const normalizedSeason = normalizeSeason(season)
  if (!VALID_SEASONS.has(normalizedSeason)) notFound()

  const seoData = seoSubjects.find(s => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const colorClass = subjectColorClasses[subj.colorKey]
  const seasonName = seasonDisplay(normalizedSeason)

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

  // Fetch this specific paper, prefer the row with both PDFs
  const { data: rows } = await supabase
    .from("papers")
    .select("id, paper_number, pdf_url, markscheme_pdf_url")
    .eq("subject_id", subjectRow.id)
    .eq("year", parsedYear)
    .eq("season", normalizedSeason)
    .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
    .order("id", { ascending: false })
    .limit(150)

  if (!rows?.length) notFound()

  const matchedRows = rows.filter((row) => normalizePaperToken(row.paper_number) === paperToken)
  if (matchedRows.length === 0) notFound()

  // Pick the best row (most files)
  const best = matchedRows.reduce((a, b) => {
    const scoreA = Number(Boolean(a.pdf_url)) + Number(Boolean(a.markscheme_pdf_url))
    const scoreB = Number(Boolean(b.pdf_url)) + Number(Boolean(b.markscheme_pdf_url))
    return scoreB > scoreA ? b : a
  })

  const validPdf = isValidPublicUrl(best.pdf_url) ? best.pdf_url : null
  const validMs = isValidPublicUrl(best.markscheme_pdf_url) ? best.markscheme_pdf_url : null
  if (!validPdf && !validMs) notFound()

  const paper: PaperRow = { ...best, pdf_url: validPdf, markscheme_pdf_url: validMs }
  const displayPaper = `Paper ${paper.paper_number}`
  const normalizedPaperSlug = toPaperSlug(paper.paper_number) ?? `paper-${paperToken}`
  const jsonLd = buildJsonLd(
    slug, subj.name, level, yearLabel, normalizedSeason, seasonName, paper.paper_number, paper, examCode
  )

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />

      <main className="min-h-screen bg-black text-white">
        {/* Sticky breadcrumb */}
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
            <Link href={`/past-papers/${slug}/${yearLabel}/${normalizedSeason}`} className="text-white/50 hover:text-white transition-colors">
              {yearLabel} {seasonName}
            </Link>
            <span className="text-white/20">›</span>
            <span className="text-white font-medium">{displayPaper}</span>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-6 py-10">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${colorClass}`}>
                Edexcel {level}
              </span>
              {examCode && (
                <span className="text-white/30 text-sm font-mono">{examCode}</span>
              )}
              <span className="text-white/30 text-sm">{yearLabel} · {seasonName}</span>
            </div>
            <h1 className="text-3xl font-extrabold mb-2">
              {subj.name} {yearLabel} {seasonName} {displayPaper}
            </h1>
            <p className="text-white/50 text-sm leading-relaxed">
              Download the free Edexcel {level} {subj.name}{examCode ? ` (${examCode})` : ""} {yearLabel} {seasonName} {displayPaper} question paper and mark scheme as PDF.
            </p>
          </div>

          {/* Download cards */}
          <div className="space-y-3">
            {validPdf && (
              <a
                href={validPdf}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between gap-4 bg-white/[0.03] border border-white/10 rounded-xl px-5 py-4 hover:bg-white/[0.06] transition-colors"
              >
                <div>
                  <p className="font-semibold text-white">
                    {subj.name} {yearLabel} {seasonName} {displayPaper} – Question Paper
                  </p>
                  <p className="text-xs text-white/40 mt-0.5">Edexcel {level}{examCode ? ` · ${examCode}` : ""} · PDF</p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30 flex-shrink-0">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download QP
                </span>
              </a>
            )}

            {validMs && (
              <a
                href={validMs}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between gap-4 bg-white/[0.03] border border-white/10 rounded-xl px-5 py-4 hover:bg-white/[0.06] transition-colors"
              >
                <div>
                  <p className="font-semibold text-white">
                    {subj.name} {yearLabel} {seasonName} {displayPaper} – Mark Scheme
                  </p>
                  <p className="text-xs text-white/40 mt-0.5">Edexcel {level}{examCode ? ` · ${examCode}` : ""} · PDF</p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30 flex-shrink-0">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Download MS
                </span>
              </a>
            )}
          </div>

          {/* SEO content block */}
          {seoData && (
            <div className="mt-12 space-y-8">
              <div className="pt-6 border-t border-white/10">
                <h2 className="text-lg font-bold mb-3">
                  About Edexcel {level} {subj.name} {yearLabel} {seasonName} {displayPaper}
                </h2>
                <p className="text-white/60 text-sm leading-relaxed mb-2">
                  This page provides free access to the official Pearson Edexcel {level}{" "}
                  {subj.name}{examCode ? ` (${examCode})` : ""} {yearLabel} {seasonName} {displayPaper}{" "}
                  question paper and mark scheme. Past papers are the most effective revision
                  resource for students preparing for their {level} {subj.name} examinations.
                  Download the PDF and practise under timed exam conditions, then check your
                  answers using the official mark scheme.
                </p>
                <p className="text-white/50 text-sm leading-relaxed">
                  {seoData.shortDescription}
                </p>
              </div>

              <div>
                <h2 className="text-base font-bold mb-3 text-white/80">How to Use This Past Paper</h2>
                <ol className="space-y-1.5 text-sm text-white/55 list-decimal list-inside leading-relaxed">
                  <li>Download the Question Paper and attempt it under timed, exam conditions.</li>
                  <li>Mark your answers using the official Mark Scheme — note where marks were lost.</li>
                  <li>Identify weak topics and revisit those sections before trying another paper.</li>
                  <li>Use GradeMax topic-wise questions to drill specific areas until confident.</li>
                </ol>
              </div>

              {/* Other papers in same session */}
              <div>
                <h2 className="text-base font-bold mb-3 text-white/80">
                  Other Papers in {subj.name} {yearLabel} {seasonName}
                </h2>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/past-papers/${slug}/${yearLabel}/${normalizedSeason}`}
                    className="text-xs px-3 py-1.5 rounded-full border border-white/15 text-white/50 hover:text-white hover:border-white/30 transition-colors"
                  >
                    All {yearLabel} {seasonName} Papers →
                  </Link>
                </div>
              </div>

              {/* Other years */}
              <div>
                <h2 className="text-base font-bold mb-3 text-white/80">
                  {displayPaper} – Other Years
                </h2>
                <div className="flex flex-wrap gap-2">
                  {seoData.yearsAvailable
                    .filter(y => y !== parsedYear)
                    .slice(-6)
                    .map(y => (
                      <Link
                        key={y}
                        href={`/past-papers/${slug}/${y}/${normalizedSeason}/${normalizedPaperSlug}`}
                        className="text-xs px-3 py-1.5 rounded-full border border-white/15 text-white/50 hover:text-white hover:border-white/30 transition-colors"
                      >
                        {subj.name} {y} {seasonName} {displayPaper}
                      </Link>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* Back navigation */}
          <div className="mt-10 pt-6 border-t border-white/10 flex flex-wrap gap-6">
            <Link
              href={`/past-papers/${slug}/${yearLabel}/${normalizedSeason}`}
              className="text-sm text-white/50 hover:text-white transition-colors"
            >
              ← {subj.name} {yearLabel} {seasonName} (All Papers)
            </Link>
            <Link
              href={`/past-papers/${slug}`}
              className="text-sm text-white/50 hover:text-white transition-colors"
            >
              ← All {subj.name} Papers
            </Link>
          </div>
        </div>
      </main>
    </>
  )
}
