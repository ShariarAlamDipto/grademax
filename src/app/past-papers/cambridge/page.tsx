
import type { Metadata } from "next"
import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { pastPaperSubjects, dbNameOf, type Subject } from "@/lib/subjects"

export const metadata: Metadata = {
  title: "Free Cambridge Past Papers – IGCSE & A Level by Year | GradeMax",
  description:
    "Browse free Cambridge (CAIE) IGCSE and International A Level past papers with mark schemes (2015–2025). Choose your subject and download question papers by year and session.",
  keywords: [
    "Cambridge past papers", "CAIE past papers", "CIE past papers",
    "Cambridge IGCSE past papers", "Cambridge A Level past papers",
    "Cambridge International past papers", "IGCSE past papers Cambridge",
    "past papers with mark schemes", "Cambridge question papers",
    "A Level question papers", "Cambridge past papers 2025",
  ],
  openGraph: {
    title: "Free Cambridge Past Papers – IGCSE & A Level by Year | GradeMax",
    description: "Browse all Cambridge IGCSE and International A Level past papers by subject, year and session. Free PDFs with mark schemes.",
    url: "https://www.grademax.me/past-papers/cambridge",
    siteName: "GradeMax",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Free Cambridge Past Papers – IGCSE & A Level | GradeMax",
    description: "All Cambridge (CAIE) past papers organised by year and session. Free PDFs with mark schemes.",
  },
  alternates: {
    canonical: "https://www.grademax.me/past-papers/cambridge",
  },
}

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: "https://www.grademax.me" },
        { "@type": "ListItem", position: 2, name: "Cambridge Past Papers", item: "https://www.grademax.me/past-papers/cambridge" },
      ],
    },
    {
      "@type": "WebPage",
      "@id": "https://www.grademax.me/past-papers/cambridge#webpage",
      url: "https://www.grademax.me/past-papers/cambridge",
      name: "Free Cambridge Past Papers 2025 – IGCSE & A Level with Mark Schemes",
      description: "Download free Cambridge IGCSE and International A Level past papers with mark schemes (2015–2025). Browse Physics, Maths, Chemistry, Biology, Computer Science and more by year and session.",
      isPartOf: { "@id": "https://www.grademax.me/#website" },
      inLanguage: "en-GB",
    },
  ],
}

// Statically rendered at build time, same as the Edexcel catalog. The set of
// subjects with papers only changes when the ingest pipeline runs, and the
// next deploy picks that up — keeps this page off the ISR write meter.
export const revalidate = false

const accentMap: Record<Subject["colorKey"], string> = {
  physics:   "accent-orange",
  maths:     "accent-blue",
  biology:   "accent-green",
  chemistry: "accent-green",
  ict:       "accent-cyan",
  english:   "accent-pink",
  other:     "accent-violet",
}

const codeColorMap: Record<Subject["colorKey"], string> = {
  physics:   "#F97316",
  maths:     "#6EA8FE",
  biology:   "#34D399",
  chemistry: "#34D399",
  ict:       "#22D3EE",
  english:   "#F472B6",
  other:     "#A78BFA",
}

export default async function CambridgePastPapersPage() {
  const subjectsWithPapers = new Set<string>()

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      { auth: { autoRefreshToken: false, persistSession: false } }
    )

    const pageSize = 1000
    let lastSeenId: string | null = null

    while (true) {
      let query = supabase
        .from("papers")
        .select("id,subjects!inner(name)")
        .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
        .order("id", { ascending: true })
        .limit(pageSize)

      if (lastSeenId) {
        query = query.gt("id", lastSeenId)
      }

      const { data: paperRows, error } = await query

      // Supabase surfaces errors via the `error` field rather than throwing.
      // Fall back to listing all known subjects so we never serve an empty
      // page just because the API was momentarily unavailable.
      if (error) {
        pastPaperSubjects.forEach(s => subjectsWithPapers.add(dbNameOf(s)))
        break
      }

      if (!paperRows || paperRows.length === 0) break

      const typedRows = paperRows as Array<{ id: string; subjects: { name: string } | { name: string }[] }>
      for (const row of typedRows) {
        const s = Array.isArray(row.subjects) ? row.subjects[0] : row.subjects
        if (s?.name) subjectsWithPapers.add(s.name)
      }

      lastSeenId = typedRows[typedRows.length - 1].id
      if (typedRows.length < pageSize) break
    }
  } catch {
    // Same fallback for transport-level errors (no network, DNS failure, etc.)
    pastPaperSubjects.forEach(s => subjectsWithPapers.add(dbNameOf(s)))
  }

  const availableSubjects = pastPaperSubjects.filter(s => subjectsWithPapers.has(dbNameOf(s)))
  const igcse = availableSubjects.filter((s) => s.level === "cambridge-igcse")
  const aLevel = availableSubjects.filter((s) => s.level === "cambridge-a-level")

  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <div style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>

        {/* Header */}
        <div style={{ marginBottom: "3rem" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.75rem" }}>
            Cambridge International (CAIE)
          </p>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            Cambridge Past Papers
          </h1>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.9rem", maxWidth: "480px", lineHeight: 1.6 }}>
            Free Cambridge IGCSE and International A Level past papers with mark schemes, organised by year and session.
          </p>
        </div>

        {/* Cambridge IGCSE */}
        {igcse.length > 0 && (
          <section style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Cambridge IGCSE
              </h2>
              <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>{igcse.length} subjects</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "0.625rem" }}>
              {igcse.map((s) => (
                <Link
                  key={s.slug}
                  href={`/past-papers/${s.slug}`}
                  className={`subject-card ${accentMap[s.colorKey]}`}
                >
                  <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--gm-text)" }}>{s.name}</p>
                  <p style={{ fontSize: "0.65rem", color: codeColorMap[s.colorKey], fontWeight: 700, letterSpacing: "0.05em", marginTop: "0.15rem" }}>
                    Cambridge IGCSE{s.examCode ? ` · ${s.examCode}` : ""}
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Cambridge International A Level */}
        {aLevel.length > 0 && (
          <section style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                International A Level
              </h2>
              <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>{aLevel.length} subjects</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "0.625rem" }}>
              {aLevel.map((s) => (
                <Link
                  key={s.slug}
                  href={`/past-papers/${s.slug}`}
                  className={`subject-card ${accentMap[s.colorKey]}`}
                >
                  <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--gm-text)" }}>{s.name}</p>
                  <p style={{ fontSize: "0.65rem", color: codeColorMap[s.colorKey], fontWeight: 700, letterSpacing: "0.05em", marginTop: "0.15rem" }}>
                    Cambridge A Level{s.examCode ? ` · ${s.examCode}` : ""}
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {availableSubjects.length === 0 || (igcse.length === 0 && aLevel.length === 0) ? (
          <div style={{ textAlign: "center", padding: "5rem 0", color: "var(--gm-text-3)" }}>
            <p style={{ fontSize: "1rem", fontWeight: 600, color: "var(--gm-text-2)", marginBottom: "0.5rem" }}>No papers available yet</p>
            <p style={{ fontSize: "0.85rem" }}>Cambridge papers are being uploaded. Check back soon.</p>
          </div>
        ) : null}

        {/* Edexcel cross-link */}
        <div style={{ border: "1px solid var(--gm-border-2)", background: "var(--gm-card-bg)", borderRadius: "1rem", padding: "1.25rem 1.5rem", marginBottom: "3rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.2rem" }}>
              Studying Pearson Edexcel?
            </p>
            <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
              Edexcel IGCSE and International A Level past papers are catalogued separately.
            </p>
          </div>
          <Link href="/past-papers" className="btn-ghost-blue" style={{ fontSize: "0.8rem", padding: "0.5rem 1.25rem", minHeight: "36px" }}>
            Edexcel Past Papers →
          </Link>
        </div>

        {/* Divider + CTA */}
        <div style={{ borderTop: "1px solid var(--gm-border)", paddingTop: "2rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
          <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", lineHeight: 1.6 }}>
            Want to practice by topic instead of by year?
          </p>
          <Link href="/subjects" className="btn-ghost-blue" style={{ fontSize: "0.8rem", padding: "0.5rem 1.25rem", minHeight: "36px" }}>
            Browse by Topic →
          </Link>
        </div>
      </div>
    </main>
  )
}
