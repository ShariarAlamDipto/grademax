import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'About Us',
  description: 'Learn about GradeMax – the free study platform helping IGCSE and A Level students prepare for Edexcel exams with past papers, worksheets, and topic-wise practice.',
  openGraph: {
    title: 'About GradeMax – Free Edexcel Past Papers Platform',
    description: 'Learn about GradeMax and how we help students prepare for Edexcel IGCSE and A Level exams.',
    url: 'https://grademax.me/about',
    siteName: 'GradeMax',
    type: 'website',
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'About GradeMax' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'About GradeMax',
    description: 'Free Edexcel IGCSE & A Level past papers, worksheets, and topic-wise practice for students worldwide.',
    images: ['/opengraph-image'],
  },
  alternates: {
    canonical: 'https://grademax.me/about',
  },
}

export default function AboutPage() {
  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "3rem 1.5rem" }}>

        <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "2.5rem" }}>
          About GradeMax
        </h1>

        <section style={{ marginBottom: "2.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "1rem" }}>Our Mission</h2>
          <p style={{ color: "var(--gm-text-2)", lineHeight: 1.7, marginBottom: "1rem" }}>
            GradeMax was created with one simple goal: to make exam preparation more efficient
            and effective for IGCSE and A Level students worldwide. Every student deserves access
            to quality study resources that help them achieve their academic goals.
          </p>
          <p style={{ color: "var(--gm-text-2)", lineHeight: 1.7 }}>
            Our platform transforms years of past examination papers into focused study materials,
            allowing students to practise exactly what they need to improve.
          </p>
        </section>

        <section style={{ marginBottom: "2.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "1rem" }}>What We Offer</h2>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "1rem" }}>
            {([
              ["Custom Worksheet Generator", "Create personalised practice papers filtered by topic, year, and difficulty level."],
              ["Instant Mark Schemes",        "Check your answers immediately with official mark schemes included."],
              ["Test Builder",                "Build custom timed tests from real exam questions and download them as PDFs."],
              ["Free Access",                 "All core features are completely free — no hidden costs or subscriptions."],
            ] as [string, string][]).map(([title, body]) => (
              <li key={title} style={{ display: "flex", gap: "0.875rem", alignItems: "flex-start" }}>
                <span style={{ color: "var(--gm-blue)", marginTop: "0.15rem", flexShrink: 0 }}>✓</span>
                <div>
                  <p style={{ fontWeight: 600, color: "var(--gm-text)", marginBottom: "0.2rem" }}>{title}</p>
                  <p style={{ color: "var(--gm-text-2)", fontSize: "0.875rem", lineHeight: 1.6 }}>{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section style={{ marginBottom: "2.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "1rem" }}>Built by Students, for Students</h2>
          <p style={{ color: "var(--gm-text-2)", lineHeight: 1.7, marginBottom: "1rem" }}>
            GradeMax was founded by students who experienced firsthand the challenges of exam
            preparation. We understand the stress of deadlines, the overwhelm of revision, and
            the need for efficient study tools.
          </p>
          <p style={{ color: "var(--gm-text-2)", lineHeight: 1.7 }}>
            Our platform is designed to address these challenges by providing smart tools that
            help you study smarter, not harder.
          </p>
        </section>

        <section>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "1rem" }}>Contact Us</h2>
          <p style={{ color: "var(--gm-text-2)", lineHeight: 1.7 }}>
            Have questions, feedback, or suggestions? We&apos;d love to hear from you.{' '}
            <a href="/contact" style={{ color: "var(--gm-blue)", textDecoration: "none" }}>Get in touch</a>.
          </p>
        </section>

      </div>
    </main>
  )
}
