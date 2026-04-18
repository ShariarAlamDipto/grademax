import { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import {
  getSubjectBySlug,
  seoSubjects,
  getLevelDisplay,
  type Level
} from '@/lib/seo-subjects'
import { generateTopicPageSchema } from '@/lib/seo-schema'

interface PageProps {
  params: Promise<{ level: string; slug: string; topic: string }>
}

const validLevels = ['igcse', 'ial'] as const

function isValidLevel(level: string): level is Level {
  return validLevels.includes(level as Level)
}

export async function generateStaticParams() {
  return seoSubjects.flatMap(subject =>
    subject.topics.map(topic => ({
      level: subject.level,
      slug: subject.slug,
      topic: topic.slug
    }))
  )
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const resolvedParams = await params
  const { level, slug, topic: topicSlug } = resolvedParams

  if (!isValidLevel(level)) return {}

  const subject = getSubjectBySlug(level, slug)
  if (!subject) return {}

  const topic = subject.topics.find(t => t.slug === topicSlug)
  if (!topic) return {}

  const title = `${topic.name} - ${subject.levelDisplay} ${subject.name} | GradeMax`
  const description = `Master ${topic.name} for ${subject.levelDisplay} ${subject.name}. ${topic.description} Practice with real exam questions and mark schemes.`

  return {
    title,
    description,
    keywords: [
      topic.name,
      `${subject.levelDisplay} ${topic.name}`,
      `${subject.name} ${topic.name}`,
      ...topic.keywords,
      ...subject.keywords.slice(0, 3)
    ],
    openGraph: {
      title,
      description,
      url: `https://grademax.me/subjects/${level}/${slug}/${topicSlug}`,
      siteName: 'GradeMax',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
    alternates: {
      canonical: `https://grademax.me/subjects/${level}/${slug}/${topicSlug}`,
    },
  }
}

export default async function TopicPage({ params }: PageProps) {
  const resolvedParams = await params
  const { level, slug, topic: topicSlug } = resolvedParams

  if (!isValidLevel(level)) notFound()

  const subject = getSubjectBySlug(level, slug)
  if (!subject) notFound()

  const topic = subject.topics.find(t => t.slug === topicSlug)
  if (!topic) notFound()

  const levelDisplay = getLevelDisplay(level)
  const schema = generateTopicPageSchema(subject, topic)

  const topicIndex = subject.topics.findIndex(t => t.slug === topicSlug)
  const prevTopic = topicIndex > 0 ? subject.topics[topicIndex - 1] : null
  const nextTopic = topicIndex < subject.topics.length - 1 ? subject.topics[topicIndex + 1] : null

  const accentColor = level === 'ial' ? '#A78BFA' : '#6EA8FE'

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />

      <main style={{ minHeight: "100vh", background: "var(--gm-bg)", color: "var(--gm-text)" }}>

        {/* Breadcrumb */}
        <nav style={{ maxWidth: "1040px", margin: "0 auto", padding: "1rem 1.5rem" }}>
          <ol style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", listStyle: "none", padding: 0, margin: 0, fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
            <li><Link href="/" className="gm-link">Home</Link></li>
            <li>/</li>
            <li><Link href={`/subjects/${level}`} className="gm-link">{levelDisplay}</Link></li>
            <li>/</li>
            <li><Link href={`/subjects/${level}/${slug}`} className="gm-link">{subject.name}</Link></li>
            <li>/</li>
            <li style={{ color: "var(--gm-text-2)" }}>{topic.name}</li>
          </ol>
        </nav>

        {/* Hero */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "1rem 1.5rem 2.5rem" }}>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: accentColor, background: `${accentColor}18`, border: `1px solid ${accentColor}28`, borderRadius: "99px", padding: "0.2rem 0.7rem" }}>
              Topic {topic.code}
            </span>
            <span style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--gm-text-3)", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "99px", padding: "0.2rem 0.7rem" }}>
              {subject.levelDisplay} {subject.name}
            </span>
          </div>

          <h1 style={{ fontSize: "clamp(1.6rem, 4vw, 2.4rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            {topic.name}
          </h1>

          <p style={{ fontSize: "1rem", color: "var(--gm-text-2)", lineHeight: 1.65, maxWidth: "600px", marginBottom: "1.5rem" }}>
            {topic.description} Master this topic with practice questions from real {subject.levelDisplay} {subject.name} past papers.
          </p>

          {/* Keywords */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginBottom: "2rem" }}>
            {topic.keywords.map(keyword => (
              <span
                key={keyword}
                className="topic-pill"
                style={{ fontSize: "0.75rem" }}
              >
                {keyword}
              </span>
            ))}
          </div>

          {/* CTAs */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            <Link
              href={`/generate?subject=${slug}&level=${level}&topic=${topic.code}`}
              className="btn-beacon"
            >
              Practice {topic.name} Questions
            </Link>
            <Link
              href={`/past-papers/${slug}`}
              className="btn-ghost-blue"
            >
              Past Papers
            </Link>
          </div>
        </section>

        {/* What You'll Learn */}
        <section style={{ borderTop: "1px solid var(--gm-border)", background: "var(--gm-surface)", padding: "2.5rem 1.5rem" }}>
          <div style={{ maxWidth: "1040px", margin: "0 auto" }}>
            <h2 style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
              What You&apos;ll Learn in {topic.name}
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.5rem" }}>
              {topic.keywords.map((keyword, index) => (
                <div
                  key={keyword}
                  style={{
                    background: "var(--gm-bg)",
                    border: "1px solid var(--gm-border-2)",
                    borderRadius: "0.75rem",
                    padding: "0.875rem 1rem",
                    display: "flex",
                    gap: "0.75rem",
                    alignItems: "flex-start",
                  }}
                >
                  <span style={{ fontSize: "0.65rem", fontWeight: 800, color: accentColor, background: `${accentColor}15`, width: "26px", height: "26px", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    {index + 1}
                  </span>
                  <div>
                    <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gm-text)", lineHeight: 1.3, textTransform: "capitalize" }}>{keyword}</p>
                    <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.2rem", lineHeight: 1.4 }}>
                      Practice {keyword} questions from {subject.levelDisplay} {subject.name} exams.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Generate Worksheet CTA */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "2.5rem 1.5rem" }}>
          <div className="gm-card" style={{ textAlign: "center", padding: "2.5rem 2rem" }}>
            <div style={{ width: "48px", height: "48px", background: `${accentColor}18`, border: `1px solid ${accentColor}28`, borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1rem" }}>
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke={accentColor} strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.5rem" }}>
              Generate a Custom Worksheet
            </h2>
            <p style={{ fontSize: "0.85rem", color: "var(--gm-text-2)", marginBottom: "1.5rem", maxWidth: "420px", margin: "0 auto 1.5rem", lineHeight: 1.6 }}>
              Create a practice worksheet with {topic.name} questions from multiple years of {subject.levelDisplay} {subject.name} past papers.
            </p>
            <Link
              href={`/generate?subject=${slug}&level=${level}&topic=${topic.code}`}
              className="btn-beacon"
            >
              Generate Worksheet
            </Link>
          </div>
        </section>

        {/* Topic Navigation */}
        <section style={{ borderTop: "1px solid var(--gm-border)", background: "var(--gm-surface)", padding: "2.5rem 1.5rem" }}>
          <div style={{ maxWidth: "1040px", margin: "0 auto" }}>
            <h2 style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
              More Topics in {subject.name}
            </h2>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginBottom: "2rem" }}>
              {subject.topics.map(t => (
                <Link
                  key={t.code}
                  href={`/subjects/${level}/${slug}/${t.slug}`}
                  style={{
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    padding: "0.35rem 0.875rem",
                    borderRadius: "99px",
                    border: `1px solid ${t.slug === topicSlug ? accentColor + "50" : "var(--gm-border-2)"}`,
                    background: t.slug === topicSlug ? `${accentColor}18` : "transparent",
                    color: t.slug === topicSlug ? accentColor : "var(--gm-text-2)",
                    textDecoration: "none",
                    transition: "all 0.15s",
                  }}
                >
                  {t.name}
                </Link>
              ))}
            </div>

            {/* Prev / Next */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "1.5rem", borderTop: "1px solid var(--gm-border)" }}>
              {prevTopic ? (
                <Link
                  href={`/subjects/${level}/${slug}/${prevTopic.slug}`}
                  className="gm-link"
                  style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem" }}
                >
                  <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                  <span>
                    <span style={{ display: "block", fontSize: "0.65rem", color: "var(--gm-text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Previous</span>
                    {prevTopic.name}
                  </span>
                </Link>
              ) : <div />}

              {nextTopic ? (
                <Link
                  href={`/subjects/${level}/${slug}/${nextTopic.slug}`}
                  className="gm-link"
                  style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", textAlign: "right" }}
                >
                  <span>
                    <span style={{ display: "block", fontSize: "0.65rem", color: "var(--gm-text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Next</span>
                    {nextTopic.name}
                  </span>
                  <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ) : <div />}
            </div>
          </div>
        </section>

        {/* Back to Subject */}
        <section style={{ maxWidth: "1040px", margin: "0 auto", padding: "2.5rem 1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--gm-border)" }}>
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.35rem" }}>
                All {subject.topics.length} topics in {subject.levelDisplay} {subject.name}
              </p>
              <Link href={`/subjects/${level}/${slug}`} className="gm-link" style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                ← Back to {subject.name}
              </Link>
            </div>
            {seoSubjects.filter(s => s.level === level && s.slug !== slug).slice(0, 3).length > 0 && (
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                {seoSubjects.filter(s => s.level === level && s.slug !== slug).slice(0, 3).map(rel => (
                  <Link key={rel.slug} href={`/subjects/${level}/${rel.slug}`} className="topic-pill" style={{ fontSize: "0.75rem" }}>
                    {rel.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </section>

      </main>
    </>
  )
}
