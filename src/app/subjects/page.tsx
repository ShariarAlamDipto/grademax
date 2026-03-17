import { Metadata } from 'next'
import Link from 'next/link'
import { seoSubjects, getSubjectsByLevel } from '@/lib/seo-subjects'
import {
  generateOrganizationSchema,
  generateBreadcrumbSchema,
  generateWebPageSchema
} from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'All Edexcel Subjects – IGCSE & A Level Past Papers by Topic',
  description: 'Browse all Edexcel IGCSE and A Level subjects on GradeMax. Access topic-wise past papers, custom worksheets, and mark schemes for Physics, Maths, Chemistry, Biology, ICT and more.',
  keywords: [
    'Edexcel subjects', 'IGCSE subjects', 'A Level subjects',
    'Edexcel IGCSE past papers', 'Edexcel A Level past papers',
    'topic wise past papers', 'past papers by topic',
    'Edexcel exam revision', 'IGCSE revision', 'A Level revision',
    'study resources Edexcel', 'free past papers',
  ],
  openGraph: {
    title: 'All Edexcel Subjects – IGCSE & A Level Past Papers by Topic',
    description: 'Browse all Edexcel IGCSE and A Level subjects. Topic-wise past papers and custom worksheets.',
    url: 'https://grademax.me/subjects',
    siteName: 'GradeMax',
    type: 'website',
  },
  alternates: {
    canonical: 'https://grademax.me/subjects',
  },
}

export default function SubjectsIndexPage() {
  const igcseSubjects = getSubjectsByLevel('igcse')
  const ialSubjects   = getSubjectsByLevel('ial')

  const baseUrl = 'https://grademax.me'
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home',     url: baseUrl },
        { name: 'Subjects', url: `${baseUrl}/subjects` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/subjects`,
        'All Subjects – IGCSE & A Level Past Papers',
        'Browse all IGCSE and A Level subjects on GradeMax.'
      )
    ]
  }

  const totalTopics = seoSubjects.reduce((acc, s) => acc + s.topics.length, 0)

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
        <div style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>

          {/* Header */}
          <div style={{ marginBottom: "3rem" }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.75rem" }}>
              Pearson Edexcel
            </p>
            <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
              All Subjects
            </h1>
            <p style={{ color: "var(--gm-text-2)", fontSize: "0.9rem", maxWidth: "480px", lineHeight: 1.6, marginBottom: "2rem" }}>
              Choose your qualification level to access past papers, topic-wise questions, and practice tools.
            </p>

            {/* Stats strip */}
            <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", paddingTop: "1.5rem", borderTop: "1px solid var(--gm-border)" }}>
              {([
                { val: seoSubjects.length.toString(), label: "Subjects" },
                { val: totalTopics.toString(),         label: "Topics" },
                { val: "2",                            label: "Levels" },
                { val: "Free",                         label: "Always" },
              ] as { val: string; label: string }[]).map(s => (
                <div key={s.label}>
                  <p style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--gm-text)", lineHeight: 1 }}>{s.val}</p>
                  <p style={{ fontSize: "0.65rem", color: "var(--gm-text-3)", marginTop: "0.25rem", letterSpacing: "0.04em" }}>{s.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* IGCSE */}
          <section style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                IGCSE Subjects
              </h2>
              <Link href="/subjects/igcse" style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", textDecoration: "none" }}>
                View all →
              </Link>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.625rem" }}>
              {igcseSubjects.map(subject => (
                <Link
                  key={subject.slug}
                  href={`/subjects/igcse/${subject.slug}`}
                  style={{
                    background: "var(--gm-surface)",
                    border: "1px solid var(--gm-border)",
                    borderRadius: "0.875rem",
                    padding: "1.25rem 1rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.4rem",
                    textDecoration: "none",
                    transition: "border-color 0.2s ease",
                  }}
                  className="gm-card"
                >
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--gm-text)" }}>{subject.name}</p>
                  <p style={{ fontSize: "0.65rem", color: "var(--gm-blue)", fontWeight: 600, letterSpacing: "0.05em" }}>{subject.examCode}</p>
                  <p style={{ fontSize: "0.75rem", color: "var(--gm-text-2)", lineHeight: 1.5, marginTop: "0.25rem" }}>{subject.shortDescription}</p>
                  <p style={{ fontSize: "0.65rem", color: "var(--gm-text-3)", marginTop: "0.5rem" }}>
                    {subject.topics.length} topics · {subject.yearsAvailable.length} years
                  </p>
                </Link>
              ))}
            </div>
          </section>

          {/* A Level */}
          <section style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                A Level (IAL) Subjects
              </h2>
              <Link href="/subjects/ial" style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", textDecoration: "none" }}>
                View all →
              </Link>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.625rem" }}>
              {ialSubjects.map(subject => (
                <Link
                  key={subject.slug}
                  href={`/subjects/ial/${subject.slug}`}
                  style={{
                    background: "var(--gm-surface)",
                    border: "1px solid var(--gm-border)",
                    borderRadius: "0.875rem",
                    padding: "1.25rem 1rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.4rem",
                    textDecoration: "none",
                    transition: "border-color 0.2s ease",
                  }}
                  className="gm-card"
                >
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--gm-text)" }}>{subject.name}</p>
                  <p style={{ fontSize: "0.65rem", color: "var(--gm-amber)", fontWeight: 600, letterSpacing: "0.05em" }}>{subject.examCode}</p>
                  <p style={{ fontSize: "0.75rem", color: "var(--gm-text-2)", lineHeight: 1.5, marginTop: "0.25rem" }}>{subject.shortDescription}</p>
                  <p style={{ fontSize: "0.65rem", color: "var(--gm-text-3)", marginTop: "0.5rem" }}>
                    {subject.topics.length} topics · {subject.yearsAvailable.length} years
                  </p>
                </Link>
              ))}
            </div>
          </section>

          {/* Footer CTA */}
          <div style={{ borderTop: "1px solid var(--gm-border)", paddingTop: "2rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
            <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", lineHeight: 1.6 }}>
              Can&apos;t find your subject? Let us know.
            </p>
            <Link href="/contact" className="btn-ghost-blue" style={{ fontSize: "0.8rem", padding: "0.5rem 1.25rem", minHeight: "36px" }}>
              Request a Subject
            </Link>
          </div>
        </div>
      </main>
    </>
  )
}
