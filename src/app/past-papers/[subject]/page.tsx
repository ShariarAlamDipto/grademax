import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { notFound } from "next/navigation"
import {
  pastPaperSubjects,
  getSubjectBySlug,
  subjectColorClasses,
} from "@/lib/subjects"

export const revalidate = 3600 // ISR: refresh every hour

// ─── Static params for all subjects with papers ────────────────────────────────

export async function generateStaticParams() {
  return pastPaperSubjects.map((s) => ({ subject: s.slug }))
}

// ─── Dynamic metadata ──────────────────────────────────────────────────────────

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
    title: `${subj.name} ${level} Past Papers – Free Download with Mark Schemes`,
    description: `Download free Edexcel ${level} ${subj.name} past papers and mark schemes from 2011 to 2025. All papers organized by year and session.`,
    openGraph: {
      title: `${subj.name} Past Papers – Edexcel ${level}`,
      description: `Download free ${subj.name} past papers with mark schemes.`,
      url: `https://grademax.me/past-papers/${slug}`,
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

interface YearGroup {
  year: number
  sessions: {
    season: string
    displaySeason: string
    papers: PaperRow[]
  }[]
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function formatSeason(season: string): string {
  const map: Record<string, string> = {
    "may-jun": "May / June",
    "oct-nov": "October / November",
    jan: "January",
    "jan-feb": "January / February",
    "feb-mar": "February / March",
  }
  return map[season.toLowerCase()] || season
}

/** Natural sort for paper numbers: 1, 1F, 1FR, 1H, 1HR, 1R, 2, 2F ... */
function paperNumberSort(a: string, b: string): number {
  const numA = parseInt(a)
  const numB = parseInt(b)
  if (numA !== numB) return numA - numB
  return a.localeCompare(b)
}

const SEASON_ORDER: Record<string, number> = {
  jan: 0,
  "jan-feb": 0,
  "feb-mar": 1,
  "may-jun": 2,
  "oct-nov": 3,
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

  // Fetch papers from Supabase using admin client (bypasses RLS for public page)
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )

  // Find subject by name + level
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
      .order("year", { ascending: false })
      .order("season", { ascending: false })

    papers = (data as PaperRow[]) || []
  }

  // Group by year → session
  const yearMap = new Map<number, Map<string, PaperRow[]>>()

  for (const paper of papers) {
    if (!yearMap.has(paper.year)) yearMap.set(paper.year, new Map())
    const sessionMap = yearMap.get(paper.year)!
    if (!sessionMap.has(paper.season)) sessionMap.set(paper.season, [])
    sessionMap.get(paper.season)!.push(paper)
  }

  const yearGroups: YearGroup[] = Array.from(yearMap.entries())
    .sort(([a], [b]) => b - a)
    .map(([year, sessionMap]) => ({
      year,
      sessions: Array.from(sessionMap.entries())
        .sort(
          ([a], [b]) =>
            (SEASON_ORDER[a.toLowerCase()] ?? 9) -
            (SEASON_ORDER[b.toLowerCase()] ?? 9)
        )
        .map(([season, sessionPapers]) => ({
          season,
          displaySeason: formatSeason(season),
          papers: sessionPapers.sort((a, b) =>
            paperNumberSort(a.paper_number, b.paper_number)
          ),
        })),
    }))

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Header */}
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
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${colorClass}`}
          >
            Edexcel {level}
          </span>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10">
        {/* Page Title */}
        <div className="mb-10">
          <h2 className="text-3xl font-extrabold mb-2">
            {subj.name} Past Papers
          </h2>
          <p className="text-white/50">
            Download free Edexcel {level} {subj.name} question papers and mark
            schemes.
          </p>
        </div>

        {/* Empty State */}
        {yearGroups.length === 0 && (
          <div className="text-center py-20 text-white/40">
            <div className="text-5xl mb-4">📄</div>
            <p className="text-lg font-medium mb-2">
              No papers available yet
            </p>
            <p className="text-sm">
              Papers for {subj.name} will be uploaded soon.
            </p>
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
                <span className="text-white/30 text-sm group-open:rotate-180 transition-transform">
                  ▼
                </span>
              </summary>

              <div className="px-6 pb-5 space-y-6">
                {yg.sessions.map((sess) => (
                  <div key={sess.season}>
                    <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3 border-b border-white/5 pb-2">
                      {sess.displaySeason}
                    </h3>

                    <div className="space-y-2">
                      {sess.papers.map((paper) => (
                        <div
                          key={paper.id}
                          className="flex items-center justify-between bg-white/[0.02] rounded-lg px-4 py-3 hover:bg-white/[0.05] transition-colors"
                        >
                          <span className="font-medium text-sm">
                            Paper {paper.paper_number}
                          </span>

                          <div className="flex gap-2">
                            {paper.pdf_url ? (
                              <a
                                href={paper.pdf_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
                                           bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30
                                           hover:bg-blue-500/25 transition-colors"
                              >
                                <svg
                                  className="w-3.5 h-3.5"
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
                              <span className="inline-flex items-center px-3 py-1.5 text-xs rounded-lg text-white/20">
                                QP —
                              </span>
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
                                <svg
                                  className="w-3.5 h-3.5"
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
                              <span className="inline-flex items-center px-3 py-1.5 text-xs rounded-lg text-white/20">
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
            </details>
          ))}
        </div>
      </div>
    </main>
  )
}
