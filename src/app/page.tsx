// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import SubjectGrid from "@/components/SubjectGrid"
import Link from "next/link"

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
    <main style={{ background: "#060912", color: "#EDF0F7", minHeight: "100vh" }}>

      {/* ════════════════════════════════════════
          § 1  HERO
          ════════════════════════════════════════ */}
      <section style={{
        minHeight: "calc(100vh - 60px)",
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
          background: "radial-gradient(ellipse at 50% -10%, rgba(110,168,254,0.07) 0%, rgba(245,158,11,0.03) 40%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div aria-hidden style={{
          position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
          width: "600px", height: "200px",
          background: "radial-gradient(ellipse at 50% 100%, rgba(110,168,254,0.04) 0%, transparent 60%)",
          pointerEvents: "none",
        }} />

        <div style={{ position: "relative", zIndex: 1, maxWidth: "780px", width: "100%" }}>
          {/* Main headline */}
          <h1
            className="hero-line-1"
            style={{
              fontSize: "clamp(3.5rem, 9vw, 6.5rem)",
              fontWeight: 800,
              lineHeight: 1.0,
              letterSpacing: "-0.04em",
              color: "#EDF0F7",
              marginBottom: "0.1em",
            }}
          >
            Your A* strategy,
          </h1>
          <h1
            className="hero-line-2"
            style={{
              fontSize: "clamp(3.5rem, 9vw, 6.5rem)",
              fontWeight: 800,
              lineHeight: 1.0,
              letterSpacing: "-0.04em",
              marginBottom: "2rem",
              background: "linear-gradient(135deg, #F59E0B 0%, #FCD34D 60%, #F97316 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            simplified.
          </h1>

          {/* Subtitle */}
          <p
            className="hero-sub"
            style={{
              fontSize: "clamp(0.8rem, 2vw, 0.95rem)",
              color: "#6B7280",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              fontWeight: 500,
              marginBottom: "2.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.75rem",
              flexWrap: "wrap",
            }}
          >
            <span>Past Papers</span>
            <span style={{ color: "#243048" }}>|</span>
            <span>Chapterwise Worksheets</span>
            <span style={{ color: "#243048" }}>|</span>
            <span>Test Builder</span>
          </p>

          {/* CTAs */}
          <div className="hero-cta" style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/generate" className="btn-beacon beacon-pulse">
              Generate Worksheet
            </Link>
            <Link href="/past-papers" className="btn-ghost-blue">
              Browse Past Papers
            </Link>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 2  SUBJECTS — float from center
          ════════════════════════════════════════ */}
      <section style={{
        borderTop: "1px solid rgba(255,255,255,0.04)",
        background: "#060912",
        padding: "5rem 1.5rem",
      }}>
        <div style={{ maxWidth: "1080px", margin: "0 auto" }}>

          {/* Section header */}
          <div style={{ textAlign: "center", marginBottom: "3.5rem" }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#F59E0B", marginBottom: "0.75rem" }}>
              Edexcel · IGCSE &amp; A Level
            </p>
            <h2 style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)", fontWeight: 800, color: "#EDF0F7", letterSpacing: "-0.03em", lineHeight: 1.1 }}>
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
          <div style={{ textAlign: "center", paddingTop: "2rem", borderTop: "1px solid rgba(255,255,255,0.04)" }}>
            <Link href="/subjects" style={{ fontSize: "0.8rem", color: "#6B7280", textDecoration: "none", transition: "color 0.15s" }} className="gm-link">
              View all subjects →
            </Link>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          § 3  WORRY CATCHER
          ════════════════════════════════════════ */}
      <section style={{ borderTop: "1px solid rgba(255,255,255,0.04)", padding: "4rem 1.5rem" }}>
        <p style={{ textAlign: "center", fontSize: "0.85rem", fontWeight: 600, color: "#EDF0F7", marginBottom: "0.35rem" }}>
          Stressed about exams?
        </p>
        <p style={{ textAlign: "center", color: "#6B7280", fontSize: "0.75rem", marginBottom: "1.75rem" }}>
          Click on your worries to catch them.
        </p>
        <LazyWorryCatcher />
      </section>

      {/* ════════════════════════════════════════
          SEO — hidden prose for crawlers
          ════════════════════════════════════════ */}
      <section style={{ padding: "2rem 1.5rem 1rem", maxWidth: "680px", margin: "0 auto" }} aria-hidden="true">
        <p style={{ fontSize: "0.75rem", color: "#1A2235", lineHeight: 1.8, textAlign: "center" }}>
          GradeMax provides free{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-gcses-and-edexcel-certificates.html"
            target="_blank" rel="noopener noreferrer" style={{ color: "#1A2235" }}>Pearson Edexcel IGCSE</a>{" "}
          and{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-advanced-levels.html"
            target="_blank" rel="noopener noreferrer" style={{ color: "#1A2235" }}>International A Level</a>{" "}
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
