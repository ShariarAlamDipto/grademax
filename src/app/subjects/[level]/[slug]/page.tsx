import { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import {
  getSubjectBySlug,
  seoSubjects,
  getLevelDisplay,
  type Level
} from '@/lib/seo-subjects'
import { generateSubjectPageSchema } from '@/lib/seo-schema'

interface PageProps {
  params: Promise<{ level: string; slug: string }>
}

const validLevels = ['igcse', 'ial'] as const

function isValidLevel(level: string): level is Level {
  return validLevels.includes(level as Level)
}

export async function generateStaticParams() {
  return seoSubjects.map(subject => ({
    level: subject.level,
    slug: subject.slug
  }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { level, slug } = await params
  if (!isValidLevel(level)) return {}
  const subject = getSubjectBySlug(level, slug)
  if (!subject) return {}
  return {
    title: subject.metaTitle,
    description: subject.metaDescription,
    keywords: subject.keywords,
    openGraph: {
      title: subject.metaTitle,
      description: subject.metaDescription,
      url: `https://grademax.me/subjects/${level}/${slug}`,
      siteName: 'GradeMax',
      type: 'website',
    },
    alternates: { canonical: `https://grademax.me/subjects/${level}/${slug}` },
  }
}

// Subjects that have a working worksheet generator
const WORKSHEET_SLUGS = new Set(['physics', 'maths-b', 'pure-mathematics-1', 'chemistry', 'biology'])

export default async function SubjectPage({ params }: PageProps) {
  const { level, slug } = await params
  if (!isValidLevel(level)) notFound()
  const subject = getSubjectBySlug(level, slug)
  if (!subject) notFound()

  const levelDisplay = getLevelDisplay(level)
  const schema = generateSubjectPageSchema(subject)
  const accentColor = level === 'ial' ? '#A78BFA' : '#6EA8FE'
  const hasWorksheet = WORKSHEET_SLUGS.has(slug)

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>

        {/* ── Hero ── */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "2.5rem 1.5rem 2rem" }}>

          {/* Breadcrumb */}
          <nav style={{ marginBottom: "1.5rem" }}>
            <ol style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", listStyle: "none", padding: 0, margin: 0 }}>
              <li><Link href="/" className="gm-link" style={{ fontSize: "0.75rem" }}>Home</Link></li>
              <li style={{ color: "var(--gm-text-3)", fontSize: "0.75rem" }}>/</li>
              <li><Link href={`/subjects/${level}`} className="gm-link" style={{ fontSize: "0.75rem" }}>{levelDisplay}</Link></li>
              <li style={{ color: "var(--gm-text-3)", fontSize: "0.75rem" }}>/</li>
              <li style={{ fontSize: "0.75rem", color: "var(--gm-text-2)" }}>{subject.name}</li>
            </ol>
          </nav>

          {/* Badges */}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: accentColor, background: `${accentColor}18`, border: `1px solid ${accentColor}28`, borderRadius: "99px", padding: "0.2rem 0.7rem" }}>
              {subject.examBoard}
            </span>
            <span style={{ fontSize: "0.6rem", fontWeight: 600, color: "var(--gm-text-3)", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "99px", padding: "0.2rem 0.7rem" }}>
              {subject.examCode}
            </span>
          </div>

          <h1 style={{ fontSize: "clamp(1.6rem, 4vw, 2.4rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            {subject.name} Past Papers
          </h1>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.875rem", lineHeight: 1.65, maxWidth: "520px", marginBottom: "2rem" }}>
            {subject.shortDescription}
          </p>

          {/* Primary actions */}
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
            <Link href={`/past-papers/${slug}`} className="btn-beacon">
              Question Papers
            </Link>
            {hasWorksheet && (
              <Link href={`/generate?subject=${slug}&level=${level}`} className="btn-ghost-blue">
                Generate Worksheet
              </Link>
            )}
          </div>

          {/* Quick stats */}
          <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", paddingTop: "1.5rem", borderTop: "1px solid var(--gm-border)" }}>
            {([
              { val: subject.topics.length.toString(), label: "Topics" },
              { val: subject.yearsAvailable.length.toString(), label: "Years" },
              { val: `${subject.yearsAvailable[0]}–${subject.yearsAvailable[subject.yearsAvailable.length - 1]}`, label: "Coverage" },
            ] as { val: string; label: string }[]).map(s => (
              <div key={s.label}>
                <p style={{ fontSize: "1rem", fontWeight: 800, color: "var(--gm-text)", lineHeight: 1 }}>{s.val}</p>
                <p style={{ fontSize: "0.62rem", color: "var(--gm-text-3)", marginTop: "0.2rem", letterSpacing: "0.04em", textTransform: "uppercase" }}>{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Topics ── */}
        <section style={{ borderTop: "1px solid var(--gm-border)", background: "var(--gm-surface)", padding: "2.5rem 1.5rem" }}>
          <div style={{ maxWidth: "1040px", margin: "0 auto" }}>
            <h2 style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
              Topics
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.5rem" }}>
              {subject.topics.map((topic, index) => (
                <div
                  key={topic.code}
                  style={{
                    background: "var(--gm-bg)",
                    border: "1px solid var(--gm-border-2)",
                    borderRadius: "0.75rem",
                    padding: "0.875rem 1rem",
                    display: "flex",
                    gap: "0.75rem",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: "0.65rem", fontWeight: 800, color: accentColor, background: `${accentColor}15`, width: "26px", height: "26px", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    {index + 1}
                  </span>
                  <p style={{ fontSize: "0.82rem", fontWeight: 500, color: "var(--gm-text)", lineHeight: 1.3 }}>{topic.name}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Past Papers by Year (SEO only — visually hidden) ── */}
        <div aria-hidden="true" style={{ position: "absolute", width: "1px", height: "1px", overflow: "hidden", clip: "rect(0,0,0,0)", whiteSpace: "nowrap" }}>
          {subject.yearsAvailable.map(year => (
            <Link key={year} href={`/past-papers/${slug}`} tabIndex={-1}>{subject.name} past papers {year}</Link>
          ))}
        </div>

        {/* ── FAQ ── */}
        <section style={{ background: "var(--gm-surface)", borderTop: "1px solid var(--gm-border)", padding: "2.5rem 1.5rem" }}>
          <div style={{ maxWidth: "600px", margin: "0 auto" }}>
            <h2 style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
              FAQ
            </h2>
            {subject.faqs.map((faq, i, arr) => (
              <details key={i} style={{ borderBottom: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                <summary style={{ padding: "0.875rem 0", cursor: "pointer", fontSize: "0.845rem", fontWeight: 500, color: "var(--gm-text)", display: "flex", justifyContent: "space-between", alignItems: "center", listStyle: "none", userSelect: "none", gap: "1rem" }}>
                  {faq.question}
                  <svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="#6B7280" strokeWidth={2.5} style={{ flexShrink: 0 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p style={{ padding: "0 0 0.875rem", fontSize: "0.82rem", color: "var(--gm-text-2)", lineHeight: 1.7 }}>{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* ── Related + CTA ── */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "2.5rem 1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1.5rem" }}>
            <div>
              <h2 style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "0.875rem" }}>
                Related Subjects
              </h2>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                {seoSubjects.filter(s => s.level === level && s.slug !== slug).slice(0, 4).map(rel => (
                  <Link key={rel.slug} href={`/past-papers/${rel.slug}`} className="topic-pill" style={{ fontSize: "0.75rem" }}>
                    {rel.name}
                  </Link>
                ))}
              </div>
            </div>
            {hasWorksheet && (
              <Link href={`/generate?subject=${slug}&level=${level}`} className="btn-beacon" style={{ flexShrink: 0, fontSize: "0.85rem", padding: "0.6rem 1.25rem", minHeight: "40px" }}>
                Free Worksheet
              </Link>
            )}
          </div>
        </section>

      </main>
    </>
  )
}
