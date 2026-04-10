import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import { getSubjectBySlug, subjectColorClasses, seasonDisplay } from "@/lib/subjects"
import { seoSubjects } from "@/lib/seo-subjects"
import { toPaperSlug } from "@/lib/paper-slugs"

export const revalidate = 3600

export function generateStaticParams() {
  const popularSubjects = [
    "physics", "chemistry", "biology", "maths-a", "maths-b", "ict",
    "pure-mathematics-1", "mechanics-1", "statistics-1",
  ]
  const recentYears = ["2025", "2024", "2023", "2022", "2021"]
  const mainSeasons = ["may-jun", "oct-nov", "jan"]
  const params: { subject: string; year: string; season: string }[] = []

  for (const subject of popularSubjects) {
    for (const year of recentYears) {
      for (const season of mainSeasons) {
        params.push({ subject, year, season })
      }
    }
  }

  return params
}

interface PaperRow {
  id: string
  paper_number: string
  pdf_url: string | null
  markscheme_pdf_url: string | null
}

const VALID_SEASONS = new Set(["jan", "jan-feb", "feb-mar", "may-jun", "oct-nov"])

function parseYearParam(value: string): number | null {
  if (!/^\d{4}$/.test(value)) return null
  const year = Number.parseInt(value, 10)
  if (year < 2000 || year > 2100) return null
  return year
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

function dedupePapers(rows: PaperRow[]): PaperRow[] {
  const byPaperNumber = new Map<string, PaperRow>()

  for (const row of rows) {
    const existing = byPaperNumber.get(row.paper_number)
    if (!existing) {
      byPaperNumber.set(row.paper_number, row)
      continue
    }

    const existingScore = Number(Boolean(existing.pdf_url)) + Number(Boolean(existing.markscheme_pdf_url))
    const rowScore = Number(Boolean(row.pdf_url)) + Number(Boolean(row.markscheme_pdf_url))

    if (rowScore > existingScore || (rowScore === existingScore && row.id > existing.id)) {
      byPaperNumber.set(row.paper_number, row)
    }
  }

  return Array.from(byPaperNumber.values()).sort((a, b) => paperSort(a.paper_number, b.paper_number))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subject: string; year: string; season: string }>
}) {
  const { subject: slug, year, season } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) return {}

  const parsedYear = parseYearParam(year)
  if (parsedYear === null) return {}
  const yearLabel = String(parsedYear)
  const normalizedSeason = normalizeSeason(season)
  if (!VALID_SEASONS.has(normalizedSeason)) return {}

  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const seasonName = seasonDisplay(normalizedSeason)
  const seoData = seoSubjects.find((s) => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const codeStr = examCode ? ` (${examCode})` : ""

  return {
    title: `Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} Past Papers – Free PDF | GradeMax`,
    description: `Download free Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} past papers with mark schemes. Official Pearson Edexcel question papers and mark schemes available as free PDF.`,
    keywords: [
      `${subj.name} ${yearLabel} ${seasonName} past paper`,
      `Edexcel ${level} ${subj.name} ${yearLabel} ${seasonName}`,
      `${subj.name} ${yearLabel} ${seasonName} mark scheme`,
      `${subj.name} past papers ${yearLabel}`,
      ...(examCode
        ? [
            `${examCode} ${yearLabel} ${seasonName} past paper`,
            `${examCode} ${yearLabel} past paper`,
            `${examCode} mark scheme ${yearLabel}`,
            `${examCode} past papers`,
          ]
        : []),
      `${subj.name} ${yearLabel} paper 1`,
      `${subj.name} ${yearLabel} paper 2`,
      `Edexcel ${subj.name} ${yearLabel} free download`,
      `${subj.name} ${yearLabel} past paper PDF`,
      `Edexcel ${level} ${subj.name} ${yearLabel}`,
      `${level} ${subj.name} ${yearLabel} ${seasonName}`,
    ],
    openGraph: {
      title: `Edexcel ${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} Past Papers | GradeMax`,
      description: `Free Edexcel ${level} ${subj.name} ${yearLabel} ${seasonName} past papers with mark schemes. Download question papers and answer booklets as PDF.`,
      url: `https://grademax.me/past-papers/${slug}/${yearLabel}/${normalizedSeason}`,
      siteName: "GradeMax",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${level} ${subj.name}${codeStr} ${yearLabel} ${seasonName} Past Papers | GradeMax`,
      description: `Free Edexcel ${level} ${subj.name} ${yearLabel} ${seasonName} papers with mark schemes.`,
    },
    alternates: {
      canonical: `https://grademax.me/past-papers/${slug}/${yearLabel}/${normalizedSeason}`,
    },
  }
}

function buildJsonLd(
  slug: string,
  subjectName: string,
  level: string,
  year: string,
  seasonSlug: string,
  seasonName: string,
  papers: PaperRow[],
  examCode: string
) {
  const base = "https://grademax.me"
  const pageUrl = `${base}/past-papers/${slug}/${year}/${seasonSlug}`

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "LearningResource",
        "@id": `${pageUrl}#resource`,
        name: `Edexcel ${level} ${subjectName} ${year} ${seasonName} Past Papers`,
        description: `Free Edexcel ${level} ${subjectName} ${year} ${seasonName} question papers and mark schemes.`,
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
        datePublished: `${year}-01-01`,
        alternativeHeadline: examCode ? `${examCode} ${year} ${seasonName}` : undefined,
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
        about: examCode
          ? {
              "@type": "Thing",
              name: `Edexcel ${level} ${subjectName} (${examCode})`,
              identifier: examCode,
            }
          : undefined,
        educationalAlignment: {
          "@type": "AlignmentObject",
          alignmentType: "educationalSubject",
          targetName: subjectName,
          educationalFramework: "Edexcel",
        },
        hasPart: [
          ...papers
            .filter((p) => p.pdf_url)
            .map((p) => ({
              "@type": "MediaObject",
              name: `${subjectName} ${year} ${seasonName} Paper ${p.paper_number} Question Paper`,
              encodingFormat: "application/pdf",
              contentUrl: p.pdf_url,
            })),
          ...papers
            .filter((p) => p.markscheme_pdf_url)
            .map((p) => ({
              "@type": "MediaObject",
              name: `${subjectName} ${year} ${seasonName} Paper ${p.paper_number} Mark Scheme`,
              encodingFormat: "application/pdf",
              contentUrl: p.markscheme_pdf_url,
            })),
        ],
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: base },
          { "@type": "ListItem", position: 2, name: "Past Papers", item: `${base}/past-papers` },
          { "@type": "ListItem", position: 3, name: subjectName, item: `${base}/past-papers/${slug}` },
          { "@type": "ListItem", position: 4, name: `${year} ${seasonName}`, item: pageUrl },
        ],
      },
    ],
  }
}

function serializeJsonLd(schema: object): string {
  return JSON.stringify(schema).replace(/</g, "\\u003c")
}

export default async function SessionPapersPage({
  params,
}: {
  params: Promise<{ subject: string; year: string; season: string }>
}) {
  const { subject: slug, year, season } = await params
  const subj = getSubjectBySlug(slug)
  if (!subj) notFound()

  const parsedYear = parseYearParam(year)
  if (parsedYear === null) notFound()
  const yearLabel = String(parsedYear)

  const seoData = seoSubjects.find((s) => s.slug === slug)
  const examCode = seoData?.examCode ?? ""
  const level = subj.level === "ial" ? "A Level" : "IGCSE"
  const colorClass = subjectColorClasses[subj.colorKey]
  const normalizedSeason = normalizeSeason(season)
  if (!VALID_SEASONS.has(normalizedSeason)) notFound()
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

  let papers: PaperRow[] = []

  if (subjectRow) {
    const { data } = await supabase
      .from("papers")
      .select("id, paper_number, pdf_url, markscheme_pdf_url")
      .eq("subject_id", subjectRow.id)
      .eq("year", parsedYear)
      .eq("season", normalizedSeason)
      .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")

    papers = dedupePapers(
      ((data as PaperRow[]) ?? [])
        .map((paper) => ({
          ...paper,
          pdf_url: isValidPublicUrl(paper.pdf_url) ? paper.pdf_url : null,
          markscheme_pdf_url: isValidPublicUrl(paper.markscheme_pdf_url) ? paper.markscheme_pdf_url : null,
        }))
        .filter((paper) => Boolean(paper.pdf_url) || Boolean(paper.markscheme_pdf_url))
    )
  }

  if (papers.length === 0) notFound()

  const jsonLd = buildJsonLd(slug, subj.name, level, yearLabel, normalizedSeason, seasonName, papers, examCode)

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }} />

      <main className="min-h-screen bg-black text-white">
        <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-6 py-3 flex items-center gap-2 text-sm flex-wrap">
            <Link href="/past-papers" className="text-white/50 hover:text-white transition-colors">Past Papers</Link>
            <span className="text-white/20">›</span>
            <Link href={`/past-papers/${slug}`} className="text-white/50 hover:text-white transition-colors">{subj.name}</Link>
            <span className="text-white/20">›</span>
            <span className="text-white font-medium">{yearLabel} {seasonName}</span>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-6 py-10">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${colorClass}`}>Edexcel {level}</span>
              <span className="text-white/30 text-sm">{yearLabel} · {seasonName}</span>
            </div>
            <h1 className="text-3xl font-extrabold mb-2">{subj.name} {yearLabel} {seasonName}</h1>
            <p className="text-white/50">
              Download free Edexcel {level} {subj.name} {yearLabel} {seasonName} question papers and mark schemes.
            </p>
          </div>

          <div className="space-y-3">
            {papers.map((paper) => {
              const paperSlug = toPaperSlug(paper.paper_number)
              return (
                <div
                  key={paper.id}
                  id={`paper-${paper.paper_number.toLowerCase()}`}
                  className="bg-white/[0.03] border border-white/10 rounded-xl px-5 py-4 flex items-center justify-between gap-4"
                >
                  <div>
                    {paperSlug ? (
                      <Link
                        href={`/past-papers/${slug}/${yearLabel}/${normalizedSeason}/${paperSlug}`}
                        className="font-semibold text-white hover:text-white/80 transition-colors"
                      >
                        Paper {paper.paper_number}
                      </Link>
                    ) : (
                      <span className="font-semibold text-white/80">Paper {paper.paper_number}</span>
                    )}
                    <span className="ml-2 text-xs text-white/30">{subj.name} · {yearLabel} · {seasonName}</span>
                  </div>

                  <div className="flex gap-2 flex-shrink-0">
                    {paper.pdf_url ? (
                      <a
                        href={paper.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30 hover:bg-blue-500/25 transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                          />
                        </svg>
                        Question Paper
                      </a>
                    ) : (
                      <span className="inline-flex items-center px-3 py-1.5 text-xs rounded-lg text-white/20">QP —</span>
                    )}

                    {paper.markscheme_pdf_url ? (
                      <a
                        href={paper.markscheme_pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30 hover:bg-emerald-500/25 transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Mark Scheme
                      </a>
                    ) : (
                      <span className="inline-flex items-center px-3 py-1.5 text-xs rounded-lg text-white/20">MS —</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {seoData && (
            <div className="mt-12 space-y-8">
              <div className="pt-6 border-t border-white/10">
                <h2 className="text-lg font-bold mb-3">About Edexcel {level} {subj.name} {yearLabel} {seasonName} Past Papers</h2>
                <p className="text-white/60 text-sm leading-relaxed mb-2">
                  This page provides free access to the official Pearson Edexcel {level} {subj.name}{examCode ? ` (${examCode})` : ""} {yearLabel} {seasonName} past papers with mark schemes.
                  These past papers are the most effective revision resource for students preparing for their {level} {subj.name} examinations.
                </p>
                <p className="text-white/50 text-sm leading-relaxed">
                  {seoData.shortDescription} The {yearLabel} {seasonName} papers cover all {seoData.topics.length} topic areas of the specification.
                </p>
              </div>

              <div>
                <h2 className="text-base font-bold mb-3 text-white/80">Topics in Edexcel {level} {subj.name}</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {seoData.topics.map((topic) => (
                    <div key={topic.slug} className="bg-white/[0.03] border border-white/10 rounded-lg px-4 py-2.5">
                      <p className="text-sm font-semibold text-white/80">{topic.name}</p>
                      <p className="text-xs text-white/40 mt-0.5 leading-snug">{topic.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h2 className="text-base font-bold mb-3 text-white/80">How to Revise with Past Papers</h2>
                <ol className="space-y-1.5 text-sm text-white/55 list-decimal list-inside leading-relaxed">
                  <li>Download the Question Paper and attempt it under timed, exam conditions.</li>
                  <li>Mark your answers using the official Mark Scheme — note where marks were lost.</li>
                  <li>Identify weak topics and revisit those sections before trying another paper.</li>
                  <li>Use GradeMax topic-wise questions to drill specific areas until confident.</li>
                </ol>
              </div>

              <div>
                <h2 className="text-base font-bold mb-3 text-white/80">Other {subj.name} Past Papers</h2>
                <div className="flex flex-wrap gap-2">
                  {seoData.yearsAvailable
                    .filter((y) => y !== parsedYear)
                    .slice(-6)
                    .map((y) => (
                      <Link
                        key={y}
                        href={`/past-papers/${slug}/${y}/${normalizedSeason}`}
                        className="text-xs px-3 py-1.5 rounded-full border border-white/15 text-white/50 hover:text-white hover:border-white/30 transition-colors"
                      >
                        {subj.name} {y} {seasonName}
                      </Link>
                    ))}
                  <Link
                    href={`/past-papers/${slug}`}
                    className="text-xs px-3 py-1.5 rounded-full border border-white/15 text-white/50 hover:text-white hover:border-white/30 transition-colors"
                  >
                    All {subj.name} Papers →
                  </Link>
                </div>
              </div>
            </div>
          )}

          <div className="mt-10 pt-6 border-t border-white/10">
            <Link href={`/past-papers/${slug}`} className="text-sm text-white/50 hover:text-white transition-colors">
              ← All {subj.name} Past Papers
            </Link>
          </div>
        </div>
      </main>
    </>
  )
}
