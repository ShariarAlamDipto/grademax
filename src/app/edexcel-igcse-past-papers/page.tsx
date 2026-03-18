import { Metadata } from 'next'
import Link from 'next/link'
import { getSubjectsByLevel } from '@/lib/seo-subjects'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'Edexcel IGCSE Past Papers 2025 – Free with Mark Schemes | All Subjects',
  description: 'Free Edexcel IGCSE past papers with mark schemes for Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), ICT (4IT1). Topic-wise questions from 2010-2025.',
  keywords: [
    'IGCSE past papers', 'IGCSE past papers Edexcel', 'Edexcel IGCSE past papers',
    'IGCSE past papers 2025', 'IGCSE past papers 2024', 'IGCSE past papers 2023', 'IGCSE past papers free',
    'IGCSE past papers with mark scheme', 'IGCSE past papers free download',
    'international GCSE past papers', 'Pearson Edexcel IGCSE',
    'IGCSE Physics past papers', 'IGCSE Maths past papers',
    'IGCSE Chemistry past papers', 'IGCSE Biology past papers',
    'IGCSE ICT past papers', 'IGCSE topic wise past papers',
    'IGCSE revision papers', 'IGCSE practice papers',
    '4PH1 past papers', '4MA1 past papers', '4MB1 past papers',
    '4CH1 past papers', '4BI1 past papers', '4IT1 past papers',
    'IGCSE question papers', 'IGCSE exam papers Edexcel',
    'IGCSE worksheets', 'IGCSE chapterwise questions',
  ],
  openGraph: {
    title: 'Edexcel IGCSE Past Papers 2025 – Free with Mark Schemes',
    description: 'Free IGCSE past papers for all Edexcel subjects with mark schemes. Organized by topic and year.',
    url: 'https://grademax.me/edexcel-igcse-past-papers',
    siteName: 'GradeMax',
    type: 'website',
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'GradeMax – Edexcel IGCSE Past Papers' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Edexcel IGCSE Past Papers 2025 – Free with Mark Schemes',
    description: 'Free IGCSE past papers for Physics, Maths, Chemistry, Biology, ICT with mark schemes.',
    images: ['/opengraph-image'],
  },
  alternates: {
    canonical: 'https://grademax.me/edexcel-igcse-past-papers',
  },
}

const faqs = [
  {
    question: "What IGCSE subjects have past papers available?",
    answer: "GradeMax offers free Edexcel IGCSE past papers for: Physics (4PH1), Mathematics A (4MA1), Mathematics B (4MB1), Chemistry (4CH1), Biology (4BI1), and ICT (4IT1). All papers include mark schemes and are organized by topic."
  },
  {
    question: "How far back do the IGCSE past papers go?",
    answer: "Most IGCSE subjects have past papers from 2014 onwards, with some subjects starting from 2015, 2017, or 2018 depending on when the specification was introduced. All available papers up to 2024 are included."
  },
  {
    question: "Can I practice IGCSE past papers by topic?",
    answer: "Yes! Every IGCSE subject on GradeMax has questions organized by topic/chapter. For example, IGCSE Physics has topics like Forces, Electricity, Waves, and Energy. You can practice all past paper questions on a specific topic."
  },
  {
    question: "What is the difference between IGCSE Maths A and Maths B?",
    answer: "IGCSE Maths A (4MA1) is the standard mathematics qualification suitable for most students. IGCSE Maths B (4MB1) is designed for higher-achieving students and includes more challenging content. Both are offered by Pearson Edexcel."
  },
  {
    question: "Are IGCSE past papers the same as GCSE past papers?",
    answer: "No. IGCSE (International GCSE) papers are set by Pearson Edexcel for international students. They differ from UK GCSE papers in content and structure. GradeMax focuses specifically on Edexcel IGCSE (International) papers."
  },
]

export default function IGCSEPastPapersPage() {
  const subjects = getSubjectsByLevel('igcse')
  const baseUrl = 'https://grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Edexcel Past Papers', url: `${baseUrl}/edexcel-past-papers` },
        { name: 'IGCSE Past Papers', url: `${baseUrl}/edexcel-igcse-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/edexcel-igcse-past-papers`,
        'Edexcel IGCSE Past Papers 2024 – Free with Mark Schemes',
        'Free Edexcel IGCSE past papers for Physics, Maths, Chemistry, Biology and ICT with mark schemes.'
      ),
      generateFAQSchema(faqs),
    ]
  }

  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      <div style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>

        {/* Breadcrumb */}
        <nav style={{ marginBottom: "1.75rem" }}>
          <ol style={{ display: "flex", alignItems: "center", gap: "0.5rem", listStyle: "none", padding: 0, margin: 0, flexWrap: "wrap" }}>
            <li><Link href="/" className="gm-link" style={{ fontSize: "0.78rem" }}>Home</Link></li>
            <li style={{ color: "var(--gm-border-2)", fontSize: "0.78rem" }}>/</li>
            <li><Link href="/edexcel-past-papers" className="gm-link" style={{ fontSize: "0.78rem" }}>Edexcel Past Papers</Link></li>
            <li style={{ color: "var(--gm-border-2)", fontSize: "0.78rem" }}>/</li>
            <li style={{ fontSize: "0.78rem", color: "var(--gm-text-2)" }}>IGCSE</li>
          </ol>
        </nav>

        {/* Header */}
        <div style={{ marginBottom: "3rem" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.75rem" }}>
            Pearson Edexcel · IGCSE
          </p>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            Edexcel IGCSE Past Papers
          </h1>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.9rem", maxWidth: "520px", lineHeight: 1.6 }}>
            Free Pearson Edexcel International GCSE past papers with mark schemes, organised by topic and year.
            Physics · Maths A &amp; B · Chemistry · Biology · ICT.
          </p>
        </div>

        {/* Subjects */}
        <section style={{ marginBottom: "3rem" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
            Choose Your Subject
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.625rem" }}>
            {subjects.map((subj) => (
              <Link
                key={subj.slug}
                href={`/subjects/igcse/${subj.slug}`}
                style={{ background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.875rem", padding: "1.25rem 1rem", display: "flex", flexDirection: "column", gap: "0.4rem", textDecoration: "none" }}
                className="gm-card"
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--gm-text)" }}>IGCSE {subj.name}</p>
                  <span style={{ fontSize: "0.6rem", color: "var(--gm-text-3)", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "4px", padding: "0.15rem 0.4rem", flexShrink: 0, marginLeft: "0.5rem" }}>{subj.examCode}</span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", lineHeight: 1.5 }}>{subj.shortDescription}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.35rem" }}>
                  {subj.topics.slice(0, 3).map((t) => (
                    <span key={t.slug} style={{ fontSize: "0.6rem", color: "var(--gm-text-3)", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "4px", padding: "0.1rem 0.4rem" }}>{t.name}</span>
                  ))}
                  {subj.topics.length > 3 && <span style={{ fontSize: "0.6rem", color: "var(--gm-text-3)" }}>+{subj.topics.length - 3} more</span>}
                </div>
                <p style={{ fontSize: "0.65rem", color: "var(--gm-text-3)", marginTop: "0.35rem" }}>
                  {subj.yearsAvailable.length} years · {subj.topics.length} topics · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
        </section>

        {/* Years */}
        <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid var(--gm-border)" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1rem" }}>
            Browse by Year
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014].map(year => (
              <Link key={year} href={`/browse?level=igcse&year=${year}`} className="topic-pill">
                {year}
              </Link>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid var(--gm-border)" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--gm-text)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.5rem" }}>
            Common Questions
          </h2>
          <div style={{ maxWidth: "640px" }}>
            {faqs.map((faq, i, arr) => (
              <details key={i} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--gm-border)" : "none" }}>
                <summary style={{ padding: "1rem 0", cursor: "pointer", fontSize: "0.875rem", fontWeight: 500, color: "var(--gm-text)", display: "flex", justifyContent: "space-between", alignItems: "center", listStyle: "none", userSelect: "none", gap: "1rem" }}>
                  {faq.question}
                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} style={{ flexShrink: 0, opacity: 0.4 }}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
                </summary>
                <p style={{ padding: "0 0 1rem", fontSize: "0.845rem", color: "var(--gm-text-2)", lineHeight: 1.75 }}>{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Related links */}
        <div style={{ borderTop: "1px solid var(--gm-border)", paddingTop: "1.5rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {([
            ["/edexcel-past-papers",      "All Edexcel Past Papers"],
            ["/edexcel-a-level-past-papers","A Level Past Papers"],
            ["/edexcel-worksheets",        "Custom Worksheets"],
            ["/generate",                  "Worksheet Generator"],
          ] as [string,string][]).map(([href, label]) => (
            <Link key={href} href={href} className="topic-pill">{label}</Link>
          ))}
        </div>
      </div>
    </main>
  )
}
