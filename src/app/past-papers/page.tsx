
import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { pastPaperSubjects, type Subject } from "@/lib/subjects"

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: "https://grademax.me" },
        { "@type": "ListItem", position: 2, name: "Past Papers", item: "https://grademax.me/past-papers" },
      ],
    },
    {
      "@type": "WebPage",
      "@id": "https://grademax.me/past-papers#webpage",
      url: "https://grademax.me/past-papers",
      name: "Free Edexcel Past Papers 2025 – IGCSE & A Level with Mark Schemes",
      description: "Download free Edexcel IGCSE and A Level past papers with mark schemes (2011–2025). Browse Physics, Maths, Chemistry, Biology, ICT and more by year and session.",
      isPartOf: { "@id": "https://grademax.me/#website" },
      inLanguage: "en-GB",
    },
  ],
}

export const revalidate = 3600

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

export default async function PastPapersPage() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )

  const { data: paperRows } = await supabase
    .from("papers")
    .select("subjects!inner(name)")
    .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")

  const subjectsWithPapers = new Set<string>(
    (paperRows ?? []).map((r: { subjects: { name: string } | { name: string }[] }) => {
      const s = Array.isArray(r.subjects) ? r.subjects[0] : r.subjects
      return s?.name ?? ""
    }).filter(Boolean)
  )

  const availableSubjects = pastPaperSubjects.filter(s => subjectsWithPapers.has(s.name))
  const igcse = availableSubjects.filter((s) => s.level === "igcse")
  const ial  = availableSubjects.filter((s) => s.level === "ial")

  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <div style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>

        {/* Header */}
        <div style={{ marginBottom: "3rem" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.75rem" }}>
            Pearson Edexcel
          </p>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            Past Papers
          </h1>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.9rem", maxWidth: "480px", lineHeight: 1.6 }}>
            Free Edexcel IGCSE and A Level past papers with mark schemes, organised by year and session.
          </p>
        </div>

        {/* IGCSE */}
        {igcse.length > 0 && (
          <section style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                IGCSE
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
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--gm-text)" }}>{s.name}</p>
                  <p style={{ fontSize: "0.65rem", color: codeColorMap[s.colorKey], fontWeight: 600, letterSpacing: "0.05em", marginTop: "0.15rem" }}>
                    Edexcel IGCSE
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* A Level */}
        {ial.length > 0 && (
          <section style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                A Level (IAL)
              </h2>
              <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>{ial.length} subjects</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "0.625rem" }}>
              {ial.map((s) => (
                <Link
                  key={s.slug}
                  href={`/past-papers/${s.slug}`}
                  className={`subject-card ${accentMap[s.colorKey]}`}
                >
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--gm-text)" }}>{s.name}</p>
                  <p style={{ fontSize: "0.65rem", color: codeColorMap[s.colorKey], fontWeight: 600, letterSpacing: "0.05em", marginTop: "0.15rem" }}>
                    Edexcel A Level
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {availableSubjects.length === 0 && (
          <div style={{ textAlign: "center", padding: "5rem 0", color: "var(--gm-text-3)" }}>
            <p style={{ fontSize: "1rem", fontWeight: 600, color: "var(--gm-text-2)", marginBottom: "0.5rem" }}>No papers available yet</p>
            <p style={{ fontSize: "0.85rem" }}>Papers are being uploaded. Check back soon.</p>
          </div>
        )}

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
