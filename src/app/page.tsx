// src/app/page.tsx
import dynamic from "next/dynamic"
import Link from "next/link"
import LazyWorryCatcher from "@/components/LazyWorryCatcher"

const SubjectGrid = dynamic(() => import("@/components/SubjectGrid"))
const FeatureCards = dynamic(() => import("@/components/FeatureCards"))

const igcseSubjects = [
  { name: "Physics",   level: "igcse", slug: "physics",   code: "4PH1",  color: "#F97316", bg: "rgba(249,115,22,0.06)",   border: "rgba(249,115,22,0.20)"   },
  { name: "Maths A",   level: "igcse", slug: "maths-a",   code: "4MA1",  color: "#6EA8FE", bg: "rgba(110,168,254,0.06)",  border: "rgba(110,168,254,0.20)"  },
  { name: "Maths B",   level: "igcse", slug: "maths-b",   code: "4MB1",  color: "#6EA8FE", bg: "rgba(110,168,254,0.06)",  border: "rgba(110,168,254,0.20)"  },
  { name: "Chemistry", level: "igcse", slug: "chemistry", code: "4CH1",  color: "#34D399", bg: "rgba(52,211,153,0.06)",   border: "rgba(52,211,153,0.20)"   },
  { name: "Biology",   level: "igcse", slug: "biology",   code: "4BI1",  color: "#34D399", bg: "rgba(52,211,153,0.06)",   border: "rgba(52,211,153,0.20)"   },
  { name: "ICT",       level: "igcse", slug: "ict",       code: "4IT1",  color: "#22D3EE", bg: "rgba(34,211,238,0.06)",   border: "rgba(34,211,238,0.20)"   },
]

const ialSubjects = [
  { name: "Pure Maths 1", level: "ial", slug: "pure-mathematics-1", code: "WMA11", color: "#A78BFA", bg: "rgba(167,139,250,0.06)", border: "rgba(167,139,250,0.20)" },
  { name: "Mechanics 1",  level: "ial", slug: "mechanics-1",        code: "WME01", color: "#F59E0B", bg: "rgba(245,158,11,0.06)",  border: "rgba(245,158,11,0.20)"  },
  { name: "Statistics 1", level: "ial", slug: "statistics-1",       code: "WST01", color: "#F472B6", bg: "rgba(244,114,182,0.06)", border: "rgba(244,114,182,0.20)" },
]

export default function Home() {
  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>

      {/* ════════════════════════════════════════
          § 1  HERO
          ════════════════════════════════════════ */}
      <section style={{
        minHeight: "calc(100vh - 68px)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        padding: "0 1.5rem 4rem",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Atmospheric glow */}
        <div aria-hidden style={{
          position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)",
          width: "900px", height: "500px",
          background: "radial-gradient(ellipse at 50% -10%, rgba(110,168,254,0.08) 0%, rgba(245,158,11,0.03) 40%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div aria-hidden style={{
          position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
          width: "600px", height: "200px",
          background: "radial-gradient(ellipse at 50% 100%, rgba(110,168,254,0.04) 0%, transparent 60%)",
          pointerEvents: "none",
        }} />

        <div style={{ position: "relative", zIndex: 1, maxWidth: "820px", width: "100%" }}>
          {/* Main headline */}
          <h1
            className="hero-line-1"
            style={{
              fontSize: "clamp(3.2rem, 9vw, 6.5rem)",
              fontWeight: 800,
              lineHeight: 1.0,
              letterSpacing: "-0.04em",
              color: "var(--gm-text)",
              marginBottom: "0.1em",
            }}
          >
            Your A* strategy,
          </h1>
          <h1
            className="hero-line-2"
            style={{
              fontSize: "clamp(3.2rem, 9vw, 6.5rem)",
              fontWeight: 800,
              lineHeight: 1.0,
              letterSpacing: "-0.04em",
              marginBottom: "1rem",
              background: "linear-gradient(135deg, #F59E0B 0%, #FCD34D 60%, #F97316 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            simplified.
          </h1>

          {/* Board labels */}
          <p style={{
            fontSize: "clamp(0.95rem, 2.5vw, 1.4rem)",
            fontWeight: 600,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--gm-text-2)",
            marginBottom: "2.5rem",
            opacity: 0.75,
          }}>
            Edexcel & Cambridge
          </p>

          {/* Subtitle — white text with subtle separators */}
          <p
            className="hero-sub"
            style={{
              fontSize: "clamp(0.82rem, 2vw, 1rem)",
              color: "var(--gm-text)",
              letterSpacing: "0.10em",
              textTransform: "uppercase",
              fontWeight: 600,
              marginBottom: "2.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.75rem",
              flexWrap: "wrap",
              opacity: 0.85,
            }}
          >
            <span>Past Papers</span>
            <span style={{ color: "var(--gm-border-2)", opacity: 0.6 }}>|</span>
            <span>Chapterwise Worksheets</span>
            <span style={{ color: "var(--gm-border-2)", opacity: 0.6 }}>|</span>
            <span>Test Builder</span>
          </p>

          {/* CTAs */}
          <div className="hero-cta" style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/generate" className="btn-beacon beacon-pulse">
              Generate Worksheet
            </Link>
            <Link href="/past-papers" className="btn-ghost-amber">
              Browse Past Papers
            </Link>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 2  STATS STRIP
          ════════════════════════════════════════ */}
      <section style={{ borderTop: "1px solid var(--gm-border)", background: "var(--gm-surface)", padding: "2.5rem 1.5rem" }}>
        <div style={{ maxWidth: "900px", margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "1.5rem", textAlign: "center" }}>
          {([
            { value: "15+",   label: "Years of papers", sub: "2010 – 2025" },
            { value: "9",     label: "Subjects",         sub: "IGCSE & A Level" },
            { value: "100%",  label: "Free",             sub: "No subscription" },
            { value: "2",     label: "Exam boards",      sub: "Edexcel & Cambridge" },
          ]).map(({ value, label, sub }) => (
            <div key={label}>
              <p style={{ fontSize: "clamp(2rem, 5vw, 2.8rem)", fontWeight: 800, color: "var(--gm-amber)", lineHeight: 1, letterSpacing: "-0.03em" }}>{value}</p>
              <p style={{ fontWeight: 700, color: "var(--gm-text)", marginTop: "0.3rem", fontSize: "0.9rem" }}>{label}</p>
              <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.1rem" }}>{sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 3  FEATURE CARDS
          ════════════════════════════════════════ */}
      <section style={{
        borderTop: "1px solid var(--gm-border)",
        background: "var(--gm-bg)",
        padding: "4rem 1.5rem",
      }}>
        <div style={{ maxWidth: "1080px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.5rem" }}>
              Everything you need
            </p>
            <h2 style={{ fontSize: "clamp(1.4rem, 3.5vw, 2rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.03em", lineHeight: 1.1 }}>
              Three tools. One platform.
            </h2>
          </div>
          <FeatureCards />
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 3  SUBJECTS — float from center
          ════════════════════════════════════════ */}
      <section style={{
        borderTop: "1px solid var(--gm-border)",
        background: "var(--gm-bg)",
        padding: "5rem 1.5rem",
      }}>
        <div style={{ maxWidth: "1080px", margin: "0 auto" }}>

          {/* Section header */}
          <div style={{ textAlign: "center", marginBottom: "3.5rem" }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.75rem" }}>
              Edexcel · IGCSE & A Level
            </p>
            <h2 style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.03em", lineHeight: 1.1 }}>
              Choose your subject
            </h2>
          </div>

          {/* IGCSE */}
          <div style={{ marginBottom: "3rem" }}>
            <SubjectGrid subjects={igcseSubjects} title="IGCSE" />
          </div>

          {/* A Level */}
          <div style={{ marginBottom: "2rem" }}>
            <SubjectGrid subjects={ialSubjects} title="A Level (IAL)" />
          </div>

          {/* View all link */}
          <div style={{ textAlign: "center", paddingTop: "2rem", borderTop: "1px solid var(--gm-border)" }}>
            <Link href="/subjects" style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", textDecoration: "none", transition: "color 0.15s" }} className="gm-link">
              View all subjects →
            </Link>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 4  WORRY CATCHER  (desktop only)
          ════════════════════════════════════════ */}
      <section className="hidden md:block" style={{ borderTop: "1px solid var(--gm-border)", padding: "4rem 1.5rem", background: "var(--gm-surface)" }}>
        <p style={{ textAlign: "center", fontSize: "0.9rem", fontWeight: 600, color: "var(--gm-text)", marginBottom: "0.35rem" }}>
          Stressed about exams?
        </p>
        <p style={{ textAlign: "center", color: "var(--gm-text-3)", fontSize: "0.78rem", marginBottom: "1.75rem" }}>
          Click on your worries to catch them.
        </p>
        <LazyWorryCatcher />
      </section>

      {/* ════════════════════════════════════════
          § 6  FAQ  (FAQPage rich snippet)
          ════════════════════════════════════════ */}
      <section style={{ borderTop: "1px solid var(--gm-border)", padding: "4rem 1.5rem", background: "var(--gm-surface)" }}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
              {
                "@type": "Question",
                "name": "Is GradeMax completely free?",
                "acceptedAnswer": { "@type": "Answer", "text": "Yes. All past papers, mark schemes, the worksheet generator, and the test builder on GradeMax are 100% free. There are no subscriptions, no paywalls, and no hidden costs." }
              },
              {
                "@type": "Question",
                "name": "Which Edexcel subjects are available on GradeMax?",
                "acceptedAnswer": { "@type": "Answer", "text": "GradeMax covers Edexcel IGCSE Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), and ICT (4IT1), plus Edexcel International A Level Pure Mathematics 1 (WMA11), Mechanics 1 (WME01), and Statistics 1 (WST01). Cambridge IGCSE papers are also available." }
              },
              {
                "@type": "Question",
                "name": "How far back do the past papers go?",
                "acceptedAnswer": { "@type": "Answer", "text": "GradeMax hosts Edexcel IGCSE and A Level past papers from 2010 all the way through to the most recent 2025 exam series, giving you over 15 years of real exam questions to practise with." }
              },
              {
                "@type": "Question",
                "name": "Are mark schemes included with the past papers?",
                "acceptedAnswer": { "@type": "Answer", "text": "Yes. Every past paper on GradeMax is accompanied by the official Pearson Edexcel or Cambridge mark scheme so you can check your answers immediately after practising." }
              },
              {
                "@type": "Question",
                "name": "How does the worksheet generator work?",
                "acceptedAnswer": { "@type": "Answer", "text": "The GradeMax worksheet generator lets you select a subject, choose specific topics, pick a year range and difficulty level, and instantly generates a PDF worksheet made up of real past paper questions — together with a mark scheme. No registration required for basic access." }
              },
              {
                "@type": "Question",
                "name": "Can I practise questions by topic?",
                "acceptedAnswer": { "@type": "Answer", "text": "Yes. GradeMax organises every question by topic and chapter so you can drill specific areas of the syllabus. Navigate to any subject page and select a topic to see all past paper questions on that topic sorted by year." }
              },
              {
                "@type": "Question",
                "name": "Does GradeMax cover Cambridge IGCSE as well as Edexcel?",
                "acceptedAnswer": { "@type": "Answer", "text": "Yes. In addition to Edexcel IGCSE and A Level papers, GradeMax also hosts Cambridge IGCSE past papers. You can find them under the Past Papers section." }
              },
            ]
          })}}
        />
        <div style={{ maxWidth: "720px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.5rem" }}>
              Got questions?
            </p>
            <h2 style={{ fontSize: "clamp(1.4rem, 3.5vw, 2rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.03em", lineHeight: 1.1 }}>
              Frequently asked questions
            </h2>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
            {([
              ["Is GradeMax completely free?", "Yes. All past papers, mark schemes, the worksheet generator, and the test builder are 100% free — no subscriptions, no paywalls."],
              ["Which subjects are available?", "Edexcel IGCSE: Physics, Maths A & B, Chemistry, Biology, ICT. Edexcel A Level: Pure Maths 1, Mechanics 1, Statistics 1. Cambridge IGCSE papers are also available."],
              ["How far back do the papers go?", "GradeMax covers 2010 through the most recent 2025 exam series — over 15 years of real Pearson Edexcel exam questions."],
              ["Are mark schemes included?", "Yes. Every paper comes with the official Pearson Edexcel or Cambridge mark scheme so you can check your answers immediately."],
              ["How does the worksheet generator work?", "Choose a subject, pick topics, set a year range and difficulty, and get a downloadable PDF of real past paper questions with a mark scheme — ready in seconds."],
              ["Can I practise questions by topic?", "Yes. Every question is tagged by topic and chapter. Open any subject page, select a topic, and see all past exam questions on exactly that area of the syllabus."],
            ] as [string, string][]).map(([q, a], i, arr) => (
              <details
                key={q}
                style={{
                  borderTop: "1px solid var(--gm-border)",
                  borderBottom: i === arr.length - 1 ? "1px solid var(--gm-border)" : undefined,
                  padding: "1.1rem 0",
                }}
              >
                <summary style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  color: "var(--gm-text)",
                  fontSize: "0.95rem",
                  listStyle: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "1rem",
                  userSelect: "none",
                }}>
                  {q}
                  <span aria-hidden style={{ flexShrink: 0, fontSize: "1.1rem", color: "var(--gm-text-3)" }}>+</span>
                </summary>
                <p style={{ marginTop: "0.75rem", color: "var(--gm-text-2)", fontSize: "0.875rem", lineHeight: 1.7, paddingRight: "1rem" }}>
                  {a}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          SEO — hidden prose for crawlers
          ════════════════════════════════════════ */}
      <section style={{ padding: "2rem 1.5rem 1rem", maxWidth: "680px", margin: "0 auto" }} aria-hidden="true">
        <p style={{ fontSize: "0.75rem", color: "var(--gm-border-2)", lineHeight: 1.8, textAlign: "center" }}>
          GradeMax provides free{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-gcses-and-edexcel-certificates.html"
            target="_blank" rel="noopener noreferrer" style={{ color: "var(--gm-border-2)" }}>Pearson Edexcel IGCSE</a>{" "}
          and{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-advanced-levels.html"
            target="_blank" rel="noopener noreferrer" style={{ color: "var(--gm-border-2)" }}>International A Level</a>{" "}
          past papers with mark schemes from 2010–2025. Topic-wise practice for Physics, Maths, Chemistry, Biology and ICT.
          Generate custom worksheets from real Pearson Edexcel exam questions.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0.25rem 1rem", marginTop: "1.25rem" }}>
          {([
            ["/edexcel-past-papers",         "Edexcel Past Papers"],
            ["/edexcel-igcse-past-papers",   "IGCSE Past Papers"],
            ["/edexcel-a-level-past-papers", "A Level Past Papers"],
            ["/edexcel-worksheets",          "Worksheet Generator"],
            ["/subjects",                    "All Subjects"],
          ] as [string, string][]).map(([href, label]) => (
            <Link key={href} href={href} className="quick-link" style={{ fontSize: "0.7rem" }}>{label}</Link>
          ))}
        </div>
      </section>

    </main>
  )
}
