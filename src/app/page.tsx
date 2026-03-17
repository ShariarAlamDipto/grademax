// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import Link from "next/link"

const subjects = [
  { name: "Physics",      level: "igcse", slug: "physics",            code: "4PH1",  accent: "accent-orange", color: "#F97316" },
  { name: "Maths A",      level: "igcse", slug: "maths-a",            code: "4MA1",  accent: "accent-blue",   color: "#6EA8FE" },
  { name: "Maths B",      level: "igcse", slug: "maths-b",            code: "4MB1",  accent: "accent-blue",   color: "#6EA8FE" },
  { name: "Chemistry",    level: "igcse", slug: "chemistry",          code: "4CH1",  accent: "accent-green",  color: "#34D399" },
  { name: "Biology",      level: "igcse", slug: "biology",            code: "4BI1",  accent: "accent-green",  color: "#34D399" },
  { name: "ICT",          level: "igcse", slug: "ict",                code: "4IT1",  accent: "accent-cyan",   color: "#22D3EE" },
  { name: "Pure Maths 1", level: "ial",   slug: "pure-mathematics-1", code: "WMA11", accent: "accent-violet", color: "#A78BFA" },
  { name: "Mechanics 1",  level: "ial",   slug: "mechanics-1",        code: "WME01", accent: "accent-amber",  color: "#F59E0B" },
  { name: "Statistics 1", level: "ial",   slug: "statistics-1",       code: "WST01", accent: "accent-pink",   color: "#F472B6" },
]

const faqs = [
  { q: "Is GradeMax free?",                                      a: "Completely free. No sign-up required for past papers or worksheets." },
  { q: "What subjects are available?",                           a: "Edexcel IGCSE: Physics, Maths A & B, Chemistry, Biology, ICT. A Level: Pure Maths 1, Mechanics 1, Statistics 1." },
  { q: "How do I generate a custom worksheet?",                  a: "Choose a subject, select topics, set difficulty and year range — download a PDF with its mark scheme in seconds." },
  { q: "Are the 2024 and 2025 papers available?",                a: "Yes. Papers are updated as Pearson releases them." },
  { q: "Can I practise by topic rather than by year?",           a: "Yes — every question is indexed by chapter so you can target weak areas directly." },
]

export default function Home() {
  return (
    <main style={{ background: "#000000", color: "#E5E7EB", minHeight: "100vh" }}>

      {/* ════════════════════════════════════════
          § 1  HERO — fills first screen
          ════════════════════════════════════════ */}
      <section style={{
        minHeight: "calc(100vh - 68px)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "0 1.5rem 3rem",
        maxWidth: "720px",
        margin: "0 auto",
        position: "relative",
      }}>
        {/* Subtle glow */}
        <div aria-hidden style={{
          position: "fixed", top: 0, left: "50%", transform: "translateX(-50%)",
          width: "800px", height: "400px",
          background: "radial-gradient(ellipse at 50% 0%, rgba(110,168,254,0.055) 0%, transparent 65%)",
          pointerEvents: "none", zIndex: 0,
        }} />

        <div style={{ position: "relative", zIndex: 1 }}>
          {/* Eyebrow */}
          <p style={{
            fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em",
            textTransform: "uppercase", color: "#F59E0B", marginBottom: "1.5rem",
          }}>
            Pearson Edexcel · IGCSE &amp; A Level
          </p>

          {/* Headline */}
          <h1 style={{
            fontSize: "clamp(2.4rem, 6vw, 4rem)",
            fontWeight: 800,
            lineHeight: 1.08,
            letterSpacing: "-0.03em",
            color: "#E5E7EB",
            marginBottom: "1.5rem",
          }}>
            Your A* strategy,{" "}
            <span style={{
              background: "linear-gradient(135deg, #F59E0B 0%, #FCD34D 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}>
              simplified.
            </span>
          </h1>

          {/* Subline */}
          <p className="hero-description" style={{
            fontSize: "clamp(1rem, 2vw, 1.125rem)",
            color: "#9CA3AF",
            lineHeight: 1.7,
            maxWidth: "480px",
            marginBottom: "2.5rem",
          }}>
            Free Edexcel past papers organised by topic, with official mark schemes.
            Build custom worksheets from real exam questions in seconds.
          </p>

          {/* CTAs */}
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "3.5rem" }}>
            <Link href="/generate" className="btn-beacon beacon-pulse">
              Generate Worksheet
            </Link>
            <Link href="/past-papers" className="btn-ghost-blue">
              Browse Past Papers
            </Link>
          </div>

          {/* Inline stats — no separate section */}
          <div style={{
            display: "flex",
            gap: "2rem",
            flexWrap: "wrap",
            paddingTop: "2rem",
            borderTop: "1px solid #1F2937",
          }}>
            {([
              { val: "1 000+", label: "Questions" },
              { val: "14+",    label: "Years" },
              { val: "9",      label: "Subjects" },
              { val: "Free",   label: "Always" },
            ] as const).map(s => (
              <div key={s.label}>
                <p style={{ fontSize: "1.25rem", fontWeight: 800, color: "#E5E7EB", lineHeight: 1 }}>{s.val}</p>
                <p style={{ fontSize: "0.7rem", color: "#6B7280", marginTop: "0.3rem", letterSpacing: "0.04em" }}>{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 2  SUBJECTS — immediately actionable
          ════════════════════════════════════════ */}
      <section style={{
        borderTop: "1px solid #1F2937",
        padding: "4rem 1.5rem",
      }}>
        <div style={{ maxWidth: "1040px", margin: "0 auto" }}>

          {/* IGCSE */}
          <div style={{ marginBottom: "3rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.8rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                IGCSE Past Papers
              </h2>
              <Link href="/edexcel-igcse-past-papers" style={{ fontSize: "0.75rem", color: "#6B7280", textDecoration: "none" }}>
                View all →
              </Link>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(148px, 1fr))", gap: "0.625rem" }}>
              {subjects.filter(s => s.level === "igcse").map(s => (
                <Link key={s.slug} href={`/subjects/${s.level}/${s.slug}`} className={`subject-card ${s.accent}`}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB" }}>{s.name}</p>
                  <p style={{ fontSize: "0.65rem", color: s.color, fontWeight: 600, letterSpacing: "0.05em", marginTop: "0.2rem" }}>{s.code}</p>
                </Link>
              ))}
            </div>
          </div>

          {/* A Level */}
          <div>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "0.8rem", fontWeight: 700, color: "#E5E7EB", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                A Level (IAL) Past Papers
              </h2>
              <Link href="/edexcel-a-level-past-papers" style={{ fontSize: "0.75rem", color: "#6B7280", textDecoration: "none" }}>
                View all →
              </Link>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(148px, 1fr))", gap: "0.625rem" }}>
              {subjects.filter(s => s.level === "ial").map(s => (
                <Link key={s.slug} href={`/subjects/${s.level}/${s.slug}`} className={`subject-card ${s.accent}`}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB" }}>{s.name}</p>
                  <p style={{ fontSize: "0.65rem", color: s.color, fontWeight: 600, letterSpacing: "0.05em", marginTop: "0.2rem" }}>{s.code}</p>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 3  FEATURES — compact 2-col list
          ════════════════════════════════════════ */}
      <section style={{
        borderTop: "1px solid #1F2937",
        background: "#0B1020",
        padding: "4rem 1.5rem",
      }}>
        <div style={{ maxWidth: "1040px", margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 3rem" }}>

            {/* Left: prose */}
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", paddingRight: "1rem" }}>
              <h2 style={{
                fontSize: "clamp(1.4rem, 3.5vw, 2rem)",
                fontWeight: 800,
                color: "#E5E7EB",
                lineHeight: 1.2,
                letterSpacing: "-0.02em",
                marginBottom: "1rem",
              }}>
                Every tool you need.<br />Nothing you don't.
              </h2>
              <p style={{ fontSize: "0.9rem", color: "#9CA3AF", lineHeight: 1.75, marginBottom: "1.5rem" }}>
                14+ years of Edexcel past papers, indexed by topic. Official mark schemes on every question.
                Custom worksheets built and downloaded in under a minute.
              </p>
              <Link href="/generate" className="btn-beacon" style={{ alignSelf: "flex-start", fontSize: "0.875rem" }}>
                Try Worksheet Generator
              </Link>
            </div>

            {/* Right: feature list */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
              {([
                ["Past Papers 2010–2025",   "Every Edexcel paper, question paper and mark scheme."],
                ["Topic-Wise Indexing",     "Filter by chapter across all years — not just by session."],
                ["Worksheet Generator",     "PDF output with mark scheme. Select topic, difficulty, year range."],
                ["Test Builder",            "Compose your own exam from hand-picked questions."],
                ["9 Subjects",              "IGCSE & IAL. More being added."],
                ["Always Free",             "No paywall. No account needed to browse."],
              ] as [string, string][]).map(([title, desc], i, arr) => (
                <div key={title} style={{
                  padding: "1rem 0",
                  borderBottom: i < arr.length - 1 ? "1px solid #1F2937" : "none",
                }}>
                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB", marginBottom: "0.2rem" }}>{title}</p>
                  <p style={{ fontSize: "0.8rem", color: "#6B7280", lineHeight: 1.6 }}>{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 4  WORRY CATCHER (stress relief)
          ════════════════════════════════════════ */}
      <section style={{ borderTop: "1px solid #1F2937", padding: "3rem 1.5rem" }}>
        <p style={{ textAlign: "center", fontSize: "0.8rem", fontWeight: 600, color: "#E5E7EB", marginBottom: "0.35rem" }}>
          Stressed about exams?
        </p>
        <p style={{ textAlign: "center", color: "#6B7280", fontSize: "0.75rem", marginBottom: "1.5rem" }}>
          Click on your worries to catch them.
        </p>
        <LazyWorryCatcher />
      </section>

      {/* ════════════════════════════════════════
          § 5  FAQ — minimal accordion
          ════════════════════════════════════════ */}
      <section style={{
        borderTop: "1px solid #1F2937",
        background: "#0B1020",
        padding: "4rem 1.5rem",
      }}>
        <div style={{ maxWidth: "620px", margin: "0 auto" }}>
          <h2 style={{
            fontSize: "1.1rem", fontWeight: 700, color: "#E5E7EB",
            marginBottom: "1.75rem", letterSpacing: "-0.01em",
          }}>
            Common questions
          </h2>
          <div>
            {faqs.map((faq, i, arr) => (
              <details key={i} style={{ borderBottom: i < arr.length - 1 ? "1px solid #1F2937" : "none" }}>
                <summary style={{
                  padding: "1rem 0",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: "#E5E7EB",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  listStyle: "none",
                  userSelect: "none",
                  gap: "1rem",
                }}>
                  {faq.q}
                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="#6B7280" strokeWidth={2.5} style={{ flexShrink: 0 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p style={{ padding: "0 0 1rem", fontSize: "0.855rem", color: "#9CA3AF", lineHeight: 1.75 }}>
                  {faq.a}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          SEO — hidden prose for crawlers
          ════════════════════════════════════════ */}
      <section style={{ padding: "2.5rem 1.5rem 1rem", maxWidth: "680px", margin: "0 auto" }} aria-hidden="true">
        <p style={{ fontSize: "0.75rem", color: "#374151", lineHeight: 1.8, textAlign: "center" }}>
          GradeMax provides free{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-gcses-and-edexcel-certificates.html"
            target="_blank" rel="noopener noreferrer" style={{ color: "#374151" }}>Pearson Edexcel IGCSE</a>{" "}
          and{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-advanced-levels.html"
            target="_blank" rel="noopener noreferrer" style={{ color: "#374151" }}>International A Level</a>{" "}
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
