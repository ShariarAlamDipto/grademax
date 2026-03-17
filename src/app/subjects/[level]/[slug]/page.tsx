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
    twitter: {
      card: 'summary_large_image',
      title: subject.metaTitle,
      description: subject.metaDescription,
    },
    alternates: {
      canonical: `https://grademax.me/subjects/${level}/${slug}`,
    },
  }
}

export default async function SubjectPage({ params }: PageProps) {
  const { level, slug } = await params
  if (!isValidLevel(level)) notFound()
  const subject = getSubjectBySlug(level, slug)
  if (!subject) notFound()

  const levelDisplay = getLevelDisplay(level)
  const schema = generateSubjectPageSchema(subject)
  const accentColor = level === 'ial' ? '#A78BFA' : '#6EA8FE'

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      <main style={{ background: "#000000", color: "#E5E7EB", minHeight: "100vh" }}>

        {/* ── Hero ── */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem 2rem" }}>

          {/* Breadcrumb */}
          <nav style={{ marginBottom: "1.75rem" }}>
            <ol style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", listStyle: "none", padding: 0, margin: 0 }}>
              <li><Link href="/" className="gm-link" style={{ fontSize: "0.78rem" }}>Home</Link></li>
              <li style={{ color: "#374151", fontSize: "0.78rem" }}>/</li>
              <li><Link href={`/subjects/${level}`} className="gm-link" style={{ fontSize: "0.78rem" }}>{levelDisplay}</Link></li>
              <li style={{ color: "#374151", fontSize: "0.78rem" }}>/</li>
              <li style={{ fontSize: "0.78rem", color: "#9CA3AF" }}>{subject.name}</li>
            </ol>
          </nav>

          {/* Badges */}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: accentColor, background: `${accentColor}18`, border: `1px solid ${accentColor}30`, borderRadius: "99px", padding: "0.25rem 0.75rem" }}>
              {subject.examBoard}
            </span>
            <span style={{ fontSize: "0.65rem", fontWeight: 600, color: "#6B7280", background: "#111827", border: "1px solid #1F2937", borderRadius: "99px", padding: "0.25rem 0.75rem" }}>
              {subject.examCode}
            </span>
          </div>

          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.6rem)", fontWeight: 800, color: "#E5E7EB", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "1rem" }}>
            {subject.h1}
          </h1>
          <p style={{ color: "#9CA3AF", fontSize: "0.95rem", lineHeight: 1.7, maxWidth: "600px", marginBottom: "2rem" }}>
            {subject.longDescription}
          </p>

          {/* Stats */}
          <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", paddingBottom: "2rem", borderBottom: "1px solid #1F2937", marginBottom: "2rem" }}>
            {([
              { val: subject.topics.length.toString(), label: "Topics" },
              { val: subject.yearsAvailable.length.toString(), label: "Years of Papers" },
              { val: `${subject.yearsAvailable[0]}–${subject.yearsAvailable[subject.yearsAvailable.length - 1]}`, label: "Coverage" },
            ] as { val: string; label: string }[]).map(s => (
              <div key={s.label}>
                <p style={{ fontSize: "1.1rem", fontWeight: 800, color: "#E5E7EB", lineHeight: 1 }}>{s.val}</p>
                <p style={{ fontSize: "0.65rem", color: "#6B7280", marginTop: "0.25rem", letterSpacing: "0.04em" }}>{s.label}</p>
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <Link href={`/generate?subject=${slug}&level=${level}`} className="btn-beacon">
              Generate Worksheet
            </Link>
            <Link href={`/past-papers/${slug}`} className="btn-ghost-blue">
              Past Papers
            </Link>
            <Link href={`/browse?subject=${slug}`} style={{ color: "#6B7280", fontSize: "0.875rem", fontWeight: 500, display: "inline-flex", alignItems: "center", padding: "0 0.5rem" }} className="gm-link">
              Browse Questions →
            </Link>
          </div>
        </section>

        {/* ── Topics ── */}
        <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", borderBottom: "1px solid #1F2937", padding: "3rem 1.5rem" }}>
          <div style={{ maxWidth: "1040px", margin: "0 auto" }}>
            <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.5rem" }}>
              {levelDisplay} {subject.name} Topics
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.625rem" }}>
              {subject.topics.map((topic, index) => (
                <Link
                  key={topic.code}
                  href={`/subjects/${level}/${slug}/${topic.slug}`}
                  style={{
                    background: "#000000",
                    border: "1px solid #1F2937",
                    borderRadius: "0.875rem",
                    padding: "1rem",
                    display: "flex",
                    gap: "0.875rem",
                    textDecoration: "none",
                    transition: "border-color 0.2s ease",
                    alignItems: "flex-start",
                  }}
                  className="gm-card"
                >
                  <span style={{ fontSize: "0.7rem", fontWeight: 800, color: accentColor, background: `${accentColor}18`, width: "28px", height: "28px", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    {index + 1}
                  </span>
                  <div>
                    <p style={{ fontSize: "0.85rem", fontWeight: 600, color: "#E5E7EB", marginBottom: "0.25rem" }}>{topic.name}</p>
                    <p style={{ fontSize: "0.75rem", color: "#6B7280", lineHeight: 1.5 }}>{topic.description}</p>
                    {topic.keywords.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.625rem" }}>
                        {topic.keywords.slice(0, 3).map(kw => (
                          <span key={kw} style={{ fontSize: "0.6rem", color: "#4B5563", background: "#111827", border: "1px solid #1F2937", borderRadius: "4px", padding: "0.1rem 0.4rem" }}>
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* ── Past Papers by Year ── */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Past Papers by Year
            </h2>
            <Link href={`/past-papers/${slug}`} style={{ fontSize: "0.72rem", color: "#6B7280", textDecoration: "none" }}>
              View all →
            </Link>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {subject.yearsAvailable.slice().reverse().map(year => (
              <Link
                key={year}
                href={`/past-papers/${slug}`}
                style={{
                  background: "#000000",
                  border: "1px solid #333333",
                  borderRadius: "0.5rem",
                  padding: "0.4rem 0.875rem",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "#9CA3AF",
                  textDecoration: "none",
                  transition: "border-color 0.15s ease, color 0.15s ease",
                }}
                className="topic-pill"
              >
                {year}
              </Link>
            ))}
          </div>
        </section>

        {/* ── FAQ ── */}
        <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", padding: "3rem 1.5rem" }}>
          <div style={{ maxWidth: "640px", margin: "0 auto" }}>
            <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.5rem" }}>
              Common Questions
            </h2>
            <div>
              {subject.faqs.map((faq, i, arr) => (
                <details key={i} style={{ borderBottom: i < arr.length - 1 ? "1px solid #1F2937" : "none" }}>
                  <summary style={{ padding: "1rem 0", cursor: "pointer", fontSize: "0.875rem", fontWeight: 500, color: "#E5E7EB", display: "flex", justifyContent: "space-between", alignItems: "center", listStyle: "none", userSelect: "none", gap: "1rem" }}>
                    {faq.question}
                    <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="#6B7280" strokeWidth={2.5} style={{ flexShrink: 0 }}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </summary>
                  <p style={{ padding: "0 0 1rem", fontSize: "0.845rem", color: "#9CA3AF", lineHeight: 1.75 }}>
                    {faq.answer}
                  </p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ── Related Subjects ── */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
            Related Subjects
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "0.625rem" }}>
            {seoSubjects
              .filter(s => s.level === level && s.slug !== slug)
              .slice(0, 3)
              .map(rel => (
                <Link
                  key={rel.slug}
                  href={`/subjects/${level}/${rel.slug}`}
                  style={{
                    background: "#000000",
                    border: "1px solid #333333",
                    borderRadius: "0.875rem",
                    padding: "1rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.35rem",
                    textDecoration: "none",
                  }}
                  className="gm-card"
                >
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB" }}>{rel.name}</p>
                  <p style={{ fontSize: "0.75rem", color: "#6B7280", lineHeight: 1.5 }}>{rel.shortDescription}</p>
                </Link>
              ))}
          </div>
        </section>

        {/* ── Bottom CTA ── */}
        <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", padding: "3rem 1.5rem" }}>
          <div style={{ maxWidth: "480px", margin: "0 auto", textAlign: "center" }}>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 800, color: "#E5E7EB", letterSpacing: "-0.02em", marginBottom: "0.75rem" }}>
              Start practising {subject.name} now
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#9CA3AF", lineHeight: 1.7, marginBottom: "1.5rem" }}>
              Generate custom worksheets from real {levelDisplay} {subject.name} past papers.
              Focus on your weak topics and ace your exams.
            </p>
            <Link href={`/generate?subject=${slug}&level=${level}`} className="btn-beacon">
              Generate Free Worksheet
            </Link>
          </div>
        </section>

      </main>
    </>
  )
}
