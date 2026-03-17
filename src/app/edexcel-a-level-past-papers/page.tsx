import { Metadata } from 'next'
import Link from 'next/link'
import { getSubjectsByLevel } from '@/lib/seo-subjects'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'Edexcel A Level Past Papers 2025 – Free IAL with Mark Schemes',
  description: 'Free Edexcel A Level (IAL) past papers with mark schemes. Pure Maths 1 (WMA11), Mechanics 1 (WME01), Statistics 1 (WST01). Topic-wise questions from 2012-2025.',
  keywords: [
    'A Level past papers', 'A Level past papers Edexcel', 'Edexcel A Level past papers',
    'A Level past papers 2025', 'A Level past papers 2024', 'A Level past papers 2023', 'A Level past papers free',
    'IAL past papers', 'International A Level past papers', 'Edexcel IAL past papers',
    'A Level Maths past papers', 'A Level Maths past papers Edexcel',
    'A Level Maths past papers by topic', 'A Level Maths topic wise',
    'Pure Maths 1 past papers', 'P1 past papers', 'WMA11 past papers',
    'Mechanics 1 past papers', 'M1 past papers', 'WME01 past papers',
    'Statistics 1 past papers', 'S1 past papers', 'WST01 past papers',
    'A Level past papers with mark scheme', 'A Level revision papers',
    'A Level question papers Edexcel', 'A Level exam papers',
    'A Level differentiation past papers', 'A Level integration past papers',
    'A Level algebra past papers', 'A Level probability past papers',
    'A Level topic wise questions', 'A Level chapterwise past papers',
    'A Level worksheets', 'A Level practice papers',
  ],
  openGraph: {
    title: 'Edexcel A Level Past Papers 2025 – Free IAL with Mark Schemes',
    description: 'Free A Level past papers for all Edexcel IAL units with mark schemes. Organized by topic and year.',
    url: 'https://grademax.me/edexcel-a-level-past-papers',
    siteName: 'GradeMax',
    type: 'website',
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'GradeMax – Edexcel A Level Past Papers' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Edexcel A Level Past Papers 2025 – Free IAL with Mark Schemes',
    description: 'Free A Level past papers for Pure Maths, Mechanics, Statistics with mark schemes.',
    images: ['/opengraph-image'],
  },
  alternates: {
    canonical: 'https://grademax.me/edexcel-a-level-past-papers',
  },
}

const faqs = [
  {
    question: "What A Level units have past papers available?",
    answer: "GradeMax offers free Edexcel IAL past papers for: Pure Mathematics 1 (WMA11/P1), Mechanics 1 (WME01/M1), and Statistics 1 (WST01/S1). More units including P2, P3, M2, S2, and Further Pure are being added."
  },
  {
    question: "What is the difference between IAL and A Level?",
    answer: "IAL (International A Level) is Pearson Edexcel's international version of A Levels, taken by students worldwide. The content is similar to UK A Levels but exams are available in January and June sessions. GradeMax focuses on Edexcel IAL papers."
  },
  {
    question: "Can I practice A Level Maths past papers by topic?",
    answer: "Yes! Each A Level unit on GradeMax has questions organized by topic. For example, Pure Maths 1 topics include Algebra, Coordinate Geometry, Sequences & Series, Differentiation, and Integration."
  },
  {
    question: "Are A Level mark schemes included?",
    answer: "Yes, every A Level past paper on GradeMax comes with its official Pearson Edexcel mark scheme. You can view the mark scheme alongside the question paper or generate worksheets with mark schemes included."
  },
  {
    question: "How do I revise for Edexcel A Level Maths?",
    answer: "1) Practice topic-wise past paper questions to master individual concepts. 2) Generate custom worksheets to mix questions from different years. 3) Do full timed papers under exam conditions. 4) Always check the mark scheme to understand the marking criteria."
  },
]

export default function ALevelPastPapersPage() {
  const subjects = getSubjectsByLevel('ial')
  const baseUrl = 'https://grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Edexcel Past Papers', url: `${baseUrl}/edexcel-past-papers` },
        { name: 'A Level Past Papers', url: `${baseUrl}/edexcel-a-level-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/edexcel-a-level-past-papers`,
        'Edexcel A Level Past Papers 2024 – Free IAL with Mark Schemes',
        'Free Edexcel IAL past papers for Pure Maths, Mechanics, Statistics with mark schemes.'
      ),
      generateFAQSchema(faqs),
    ]
  }

  return (
    <main style={{ background: "#000000", color: "#E5E7EB", minHeight: "100vh" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      <div style={{ maxWidth: "1040px", margin: "0 auto", padding: "3rem 1.5rem" }}>

        {/* Breadcrumb */}
        <nav style={{ marginBottom: "1.75rem" }}>
          <ol style={{ display: "flex", alignItems: "center", gap: "0.5rem", listStyle: "none", padding: 0, margin: 0, flexWrap: "wrap" }}>
            <li><Link href="/" className="gm-link" style={{ fontSize: "0.78rem" }}>Home</Link></li>
            <li style={{ color: "#374151", fontSize: "0.78rem" }}>/</li>
            <li><Link href="/edexcel-past-papers" className="gm-link" style={{ fontSize: "0.78rem" }}>Edexcel Past Papers</Link></li>
            <li style={{ color: "#374151", fontSize: "0.78rem" }}>/</li>
            <li style={{ fontSize: "0.78rem", color: "#9CA3AF" }}>A Level</li>
          </ol>
        </nav>

        {/* Header */}
        <div style={{ marginBottom: "3rem" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#A78BFA", marginBottom: "0.75rem" }}>
            Pearson Edexcel · IAL
          </p>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "#E5E7EB", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            Edexcel A Level (IAL) Past Papers
          </h1>
          <p style={{ color: "#9CA3AF", fontSize: "0.9rem", maxWidth: "520px", lineHeight: 1.6 }}>
            Free Pearson Edexcel International A Level past papers with mark schemes.
            Pure Maths 1 · Mechanics 1 · Statistics 1.
          </p>
        </div>

        {/* Units */}
        <section style={{ marginBottom: "3rem" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
            A Level Units Available
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.625rem" }}>
            {subjects.map((subj) => (
              <Link
                key={subj.slug}
                href={`/subjects/ial/${subj.slug}`}
                style={{ background: "#000000", border: "1px solid #333333", borderRadius: "0.875rem", padding: "1.25rem 1rem", display: "flex", flexDirection: "column", gap: "0.4rem", textDecoration: "none" }}
                className="gm-card"
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB" }}>{subj.name}</p>
                  <span style={{ fontSize: "0.6rem", color: "#6B7280", background: "#111827", border: "1px solid #1F2937", borderRadius: "4px", padding: "0.15rem 0.4rem", flexShrink: 0, marginLeft: "0.5rem" }}>{subj.examCode}</span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "#6B7280", lineHeight: 1.5 }}>{subj.shortDescription}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.35rem" }}>
                  {subj.topics.map((t) => (
                    <span key={t.slug} style={{ fontSize: "0.6rem", color: "#4B5563", background: "#111827", border: "1px solid #1F2937", borderRadius: "4px", padding: "0.1rem 0.4rem" }}>{t.name}</span>
                  ))}
                </div>
                <p style={{ fontSize: "0.65rem", color: "#4B5563", marginTop: "0.35rem" }}>
                  {subj.yearsAvailable.length} years · {subj.topics.length} topics · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
        </section>

        {/* Topic links */}
        <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid #1F2937" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
            Browse by Topic
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1.5rem" }}>
            {subjects.map((subj) => (
              <div key={subj.slug}>
                <p style={{ fontSize: "0.72rem", fontWeight: 700, color: "#A78BFA", marginBottom: "0.625rem", letterSpacing: "0.04em" }}>{subj.name}</p>
                <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  {subj.topics.map((topic) => (
                    <li key={topic.slug}>
                      <Link href={`/subjects/ial/${subj.slug}/${topic.slug}`} className="gm-link" style={{ fontSize: "0.8rem" }}>
                        {topic.name} →
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* Years */}
        <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid #1F2937" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1rem" }}>
            Browse by Year
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014].map(year => (
              <Link key={year} href={`/browse?level=ial&year=${year}`} className="topic-pill">
                {year}
              </Link>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid #1F2937" }}>
          <h2 style={{ fontSize: "0.75rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "1.5rem" }}>
            Common Questions
          </h2>
          <div style={{ maxWidth: "640px" }}>
            {faqs.map((faq, i, arr) => (
              <details key={i} style={{ borderBottom: i < arr.length - 1 ? "1px solid #1F2937" : "none" }}>
                <summary style={{ padding: "1rem 0", cursor: "pointer", fontSize: "0.875rem", fontWeight: 500, color: "#E5E7EB", display: "flex", justifyContent: "space-between", alignItems: "center", listStyle: "none", userSelect: "none", gap: "1rem" }}>
                  {faq.question}
                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="#6B7280" strokeWidth={2.5} style={{ flexShrink: 0 }}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
                </summary>
                <p style={{ padding: "0 0 1rem", fontSize: "0.845rem", color: "#9CA3AF", lineHeight: 1.75 }}>{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Related links */}
        <div style={{ borderTop: "1px solid #1F2937", paddingTop: "1.5rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {([
            ["/edexcel-past-papers",       "All Edexcel Past Papers"],
            ["/edexcel-igcse-past-papers", "IGCSE Past Papers"],
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
