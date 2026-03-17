// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import Link from "next/link"

const subjects = [
  { name: "Physics",      level: "igcse", slug: "physics",            code: "4PH1",  accent: "accent-orange", color: "#F97316", questions: "650+" },
  { name: "Maths A",      level: "igcse", slug: "maths-a",            code: "4MA1",  accent: "accent-blue",   color: "#6EA8FE", questions: "820+" },
  { name: "Maths B",      level: "igcse", slug: "maths-b",            code: "4MB1",  accent: "accent-blue",   color: "#6EA8FE", questions: "780+" },
  { name: "Chemistry",    level: "igcse", slug: "chemistry",          code: "4CH1",  accent: "accent-green",  color: "#34D399", questions: "590+" },
  { name: "Biology",      level: "igcse", slug: "biology",            code: "4BI1",  accent: "accent-green",  color: "#34D399", questions: "540+" },
  { name: "ICT",          level: "igcse", slug: "ict",                code: "4IT1",  accent: "accent-cyan",   color: "#22D3EE", questions: "310+" },
  { name: "Pure Maths 1", level: "ial",   slug: "pure-mathematics-1", code: "WMA11", accent: "accent-violet", color: "#A78BFA", questions: "480+" },
  { name: "Mechanics 1",  level: "ial",   slug: "mechanics-1",        code: "WME01", accent: "accent-amber",  color: "#F59E0B", questions: "260+" },
  { name: "Statistics 1", level: "ial",   slug: "statistics-1",       code: "WST01", accent: "accent-pink",   color: "#F472B6", questions: "220+" },
]

const popularTopics = [
  { name: "Forces & Motion",    href: "/subjects/igcse/physics/forces-and-motion" },
  { name: "Electricity",        href: "/subjects/igcse/physics/electricity" },
  { name: "Algebra",            href: "/subjects/igcse/maths-b/algebra" },
  { name: "Trigonometry",       href: "/subjects/igcse/maths-b/trigonometry" },
  { name: "Organic Chemistry",  href: "/subjects/igcse/chemistry/organic-chemistry" },
  { name: "Genetics",           href: "/subjects/igcse/biology/reproduction-inheritance" },
  { name: "Differentiation",    href: "/subjects/ial/pure-mathematics-1/differentiation" },
  { name: "SUVAT & Kinematics", href: "/subjects/ial/mechanics-1/kinematics" },
  { name: "Probability",        href: "/subjects/ial/statistics-1/probability" },
  { name: "Waves",              href: "/subjects/igcse/physics/waves" },
  { name: "Number",             href: "/subjects/igcse/maths-a/number" },
  { name: "Geometry",           href: "/subjects/igcse/maths-a/geometry" },
]

const faqs = [
  { q: "Where can I find free Edexcel past papers?",            a: "GradeMax provides free Edexcel IGCSE and A Level past papers for Physics, Maths, Chemistry, Biology, and ICT. All papers include mark schemes and are organised by topic and year from 2010–2025." },
  { q: "Can I practise Edexcel past papers by topic?",          a: "Yes — all questions are organised by topic. Browse a specific chapter such as Electricity, Forces, Algebra, or Differentiation and practise with instant mark scheme access." },
  { q: "Is GradeMax free?",                                     a: "Completely free. No sign-up required for browsing past papers and generating worksheets." },
  { q: "What subjects are available?",                          a: "GradeMax covers Edexcel IGCSE Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), ICT (4IT1), and A Level Pure Maths 1 (WMA11), Mechanics 1 (WME01), Statistics 1 (WST01)." },
  { q: "How do I generate custom worksheets?",                  a: "Use the Worksheet Generator — select your subject, pick topics, set difficulty and year range, then download a PDF with its matching mark scheme in seconds." },
  { q: "Does GradeMax have Edexcel 2024 and 2025 past papers?", a: "Yes. GradeMax is updated regularly as Pearson releases new papers and mark schemes." },
]

const features = [
  { title: "14+ Years of Past Papers",  desc: "Every Pearson Edexcel question paper from 2010–2025, question papers and mark schemes in one place.",                                      wide: true  },
  { title: "Topic-Wise Practice",       desc: "Drill the exact topics you are weak on. Every question indexed by chapter across all years."                                                           },
  { title: "Instant Worksheets",        desc: "Select subject, topics, difficulty and year range. A PDF worksheet with its mark scheme is ready in seconds.",  amber: true, tall: true  },
  { title: "Official Mark Schemes",     desc: "Every question is paired with the real Edexcel mark scheme so you know precisely what the examiner expects."                                          },
  { title: "Test Builder",              desc: "Hand-pick questions from different years and topics to compose your own timed practice paper."                                                         },
  { title: "9 Subjects",                desc: "IGCSE Physics, Maths A & B, Chemistry, Biology, ICT — plus IAL Pure Maths, Mechanics and Statistics.",                                  wide: true  },
  { title: "Always Free",               desc: "No paywalls. No account required. Every past paper and mark scheme is free."                                                                          },
  { title: "PDF Download",              desc: "Download any paper or generated worksheet as a clean, print-ready PDF."                                                                               },
]

export default function Home() {
  const igcseSubjects = subjects.filter(s => s.level === "igcse")
  const ialSubjects   = subjects.filter(s => s.level === "ial")

  return (
    <main style={{ background: "#000000", color: "#E5E7EB", minHeight: "100vh" }}>

      {/* ── HERO ── */}
      <section style={{
        padding: "clamp(4rem,10vw,7rem) 1.5rem clamp(3rem,6vw,5rem)",
        textAlign: "center",
        position: "relative",
        overflow: "hidden",
      }}>
        <div aria-hidden style={{
          position: "absolute", top: "10%", left: "50%", transform: "translateX(-50%)",
          width: "600px", height: "300px",
          background: "radial-gradient(ellipse, rgba(110,168,254,0.06) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        <p style={{ color: "#F59E0B", fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: "1.25rem" }}>
          Pearson Edexcel · IGCSE &amp; A Level
        </p>

        <h1 style={{
          fontSize: "clamp(2.2rem,5.5vw,3.75rem)", fontWeight: 800, lineHeight: 1.12,
          letterSpacing: "-0.025em", color: "#E5E7EB",
          marginBottom: "1.25rem", maxWidth: "780px", marginLeft: "auto", marginRight: "auto",
        }}>
          Your A* Strategy,{" "}
          <span style={{ background: "linear-gradient(135deg,#F59E0B 0%,#FCD34D 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
            Simplified
          </span>
        </h1>

        <p className="hero-description" style={{ color: "#9CA3AF", fontSize: "clamp(1rem,2vw,1.15rem)", lineHeight: 1.7, maxWidth: "520px", margin: "0 auto 0.75rem" }}>
          Free Edexcel IGCSE &amp; A Level past papers organised by topic, with official mark schemes.
          Generate custom worksheets from real exam questions.
        </p>
        <p style={{ color: "#6B7280", fontSize: "0.78rem", marginBottom: "2.75rem" }}>
          14 years of Pearson Edexcel papers · 9 subjects · 1 000+ questions · Always free
        </p>

        <div style={{ display: "flex", gap: "0.875rem", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/generate" className="btn-beacon beacon-pulse" style={{ fontSize: "0.9rem" }}>
            Generate Worksheet
          </Link>
          <Link href="/past-papers" className="btn-ghost-blue" style={{ fontSize: "0.9rem" }}>
            Browse Past Papers
          </Link>
        </div>
      </section>

      {/* ── STATS STRIP ── */}
      <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", borderBottom: "1px solid #1F2937", padding: "1.5rem" }}>
        <div style={{ maxWidth: "700px", margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(4,1fr)", textAlign: "center", gap: "1rem" }}>
          {([
            { val: "1 000+", label: "Questions",       color: "#34D399" },
            { val: "14+",    label: "Years of Papers", color: "#6EA8FE" },
            { val: "9",      label: "Subjects",        color: "#F59E0B" },
            { val: "Free",   label: "Always",          color: "#34D399" },
          ] as const).map(s => (
            <div key={s.label}>
              <p style={{ fontSize: "clamp(1.3rem,3vw,1.8rem)", fontWeight: 800, color: s.color, lineHeight: 1.2 }}>{s.val}</p>
              <p style={{ fontSize: "0.7rem", color: "#9CA3AF", marginTop: "0.25rem", letterSpacing: "0.04em" }}>{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── BENTO FEATURE GRID ── */}
      <section style={{ padding: "5rem 1.5rem", maxWidth: "1080px", margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: "3rem" }}>
          <p style={{ color: "#6EA8FE", fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "0.75rem" }}>Everything You Need</p>
          <h2 style={{ fontSize: "clamp(1.6rem,4vw,2.4rem)", fontWeight: 800, color: "#E5E7EB", lineHeight: 1.2, marginBottom: "0.75rem" }}>Built for Exam Success</h2>
          <p style={{ color: "#9CA3AF", maxWidth: "400px", margin: "0 auto", fontSize: "0.925rem" }}>Every tool you need to go from uncertain to confident — organised, fast, and free.</p>
        </div>

        <div className="bento-grid">
          {features.map(f => (
            <div
              key={f.title}
              className={`gm-card${f.amber ? " gm-card-amber" : ""} ${f.wide ? "bento-wide" : ""} ${f.tall ? "bento-tall" : ""}`}
              style={{
                padding: "1.75rem 2rem",
                background: f.amber ? "linear-gradient(135deg,#0B1020 60%,rgba(245,158,11,0.05) 100%)" : "#0B1020",
                minHeight: f.tall ? "240px" : undefined,
                display: "flex", flexDirection: "column", gap: "0.625rem",
              }}
            >
              <h3 style={{ fontSize: "0.975rem", fontWeight: 700, color: f.amber ? "#F59E0B" : "#E5E7EB", lineHeight: 1.3 }}>{f.title}</h3>
              <p style={{ fontSize: "0.855rem", color: "#9CA3AF", lineHeight: 1.7, flexGrow: 1 }}>{f.desc}</p>
              {f.amber && (
                <Link href="/generate" className="btn-beacon" style={{ fontSize: "0.78rem", padding: "0.45rem 0.9rem", alignSelf: "flex-start", minHeight: "34px", borderRadius: "0.45rem", marginTop: "0.5rem" }}>
                  Try it free
                </Link>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── SUBJECT EXPLORER ── */}
      <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", borderBottom: "1px solid #1F2937", padding: "5rem 1.5rem" }}>
        <div style={{ maxWidth: "1080px", margin: "0 auto" }}>

          {/* IGCSE */}
          <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
            <p style={{ color: "#6EA8FE", fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "0.75rem" }}>Subject Explorer</p>
            <h2 style={{ fontSize: "clamp(1.5rem,4vw,2.2rem)", fontWeight: 800, color: "#E5E7EB", lineHeight: 1.2 }}>Edexcel IGCSE Past Papers</h2>
            <p style={{ color: "#9CA3AF", marginTop: "0.5rem", fontSize: "0.9rem" }}>Free Pearson Edexcel question papers &amp; mark schemes</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(155px,1fr))", gap: "0.75rem", marginBottom: "1.5rem" }}>
            {igcseSubjects.map(s => (
              <Link key={s.slug} href={`/subjects/${s.level}/${s.slug}`} className={`subject-card ${s.accent}`}>
                <p style={{ fontSize: "0.85rem", fontWeight: 700, color: "#E5E7EB", lineHeight: 1.35 }}>{s.name}</p>
                <p style={{ fontSize: "0.68rem", color: s.color, fontWeight: 600, letterSpacing: "0.04em" }}>{s.code}</p>
                <p style={{ fontSize: "0.68rem", color: "#6B7280", marginTop: "0.25rem" }}>{s.questions} questions</p>
              </Link>
            ))}
          </div>

          <div style={{ textAlign: "center", marginBottom: "4.5rem" }}>
            <Link href="/edexcel-igcse-past-papers" style={{ color: "#6EA8FE", fontSize: "0.8rem", textDecoration: "none" }}>
              View all IGCSE past papers →
            </Link>
          </div>

          {/* IAL */}
          <div style={{ textAlign: "center", marginBottom: "2rem" }}>
            <h2 style={{ fontSize: "clamp(1.5rem,4vw,2.2rem)", fontWeight: 800, color: "#E5E7EB", lineHeight: 1.2 }}>Edexcel A Level (IAL) Past Papers</h2>
            <p style={{ color: "#9CA3AF", marginTop: "0.5rem", fontSize: "0.9rem" }}>Free Pearson Edexcel International A Level papers</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(155px,1fr))", gap: "0.75rem" }}>
            {ialSubjects.map(s => (
              <Link key={s.slug} href={`/subjects/${s.level}/${s.slug}`} className={`subject-card ${s.accent}`}>
                <p style={{ fontSize: "0.85rem", fontWeight: 700, color: "#E5E7EB", lineHeight: 1.35 }}>{s.name}</p>
                <p style={{ fontSize: "0.68rem", color: s.color, fontWeight: 600, letterSpacing: "0.04em" }}>{s.code}</p>
                <p style={{ fontSize: "0.68rem", color: "#6B7280", marginTop: "0.25rem" }}>{s.questions} questions</p>
              </Link>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: "1.5rem" }}>
            <Link href="/edexcel-a-level-past-papers" style={{ color: "#A78BFA", fontSize: "0.8rem", textDecoration: "none" }}>
              View all A Level past papers →
            </Link>
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section style={{ padding: "5rem 1.5rem", maxWidth: "900px", margin: "0 auto" }}>
        <h2 style={{ fontSize: "clamp(1.5rem,3.5vw,2.2rem)", fontWeight: 800, color: "#E5E7EB", textAlign: "center", marginBottom: "3rem", letterSpacing: "-0.015em" }}>
          Three Steps to Exam Confidence
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: "1rem" }}>
          {([
            { step: "01", title: "Pick a Subject",      desc: "Choose from 9 Edexcel IGCSE and A Level subjects, each organised by topic and year.",                                  color: "#6EA8FE" },
            { step: "02", title: "Target Weak Topics",  desc: "Browse questions chapter by chapter. Focus your revision precisely where it will make the most difference.",           color: "#F59E0B" },
            { step: "03", title: "Generate & Download", desc: "Build a custom worksheet from real exam questions. Download it with its official mark scheme as a PDF.",               color: "#34D399" },
          ] as const).map(item => (
            <div key={item.step} style={{ background: "#0B1020", border: "1px solid #333333", borderRadius: "0.875rem", padding: "1.75rem 2rem" }}>
              <p style={{ fontSize: "2.25rem", fontWeight: 800, color: item.color, opacity: 0.2, lineHeight: 1, marginBottom: "1rem", fontVariantNumeric: "tabular-nums" }}>{item.step}</p>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#E5E7EB", marginBottom: "0.5rem" }}>{item.title}</h3>
              <p style={{ fontSize: "0.855rem", color: "#9CA3AF", lineHeight: 1.7 }}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── POPULAR TOPICS ── */}
      <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", borderBottom: "1px solid #1F2937", padding: "3rem 1.5rem" }}>
        <div style={{ maxWidth: "900px", margin: "0 auto" }}>
          <p style={{ textAlign: "center", fontSize: "0.7rem", fontWeight: 700, color: "#6B7280", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "1.5rem" }}>
            Popular Topics
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0.5rem" }}>
            {popularTopics.map(t => (
              <Link key={t.href} href={t.href} className="topic-pill">{t.name}</Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── WHY PAST PAPERS ── */}
      <section style={{ padding: "5rem 1.5rem", maxWidth: "680px", margin: "0 auto" }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, color: "#E5E7EB", textAlign: "center", marginBottom: "1.5rem", letterSpacing: "-0.01em" }}>
          Why Practise with Edexcel Past Papers?
        </h2>
        <p style={{ color: "#9CA3AF", fontSize: "0.9rem", lineHeight: 1.8, marginBottom: "1rem" }}>
          Past papers are the most effective way to prepare for{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-gcses-and-edexcel-certificates.html" target="_blank" rel="noopener noreferrer" style={{ color: "#6EA8FE", textDecoration: "none" }}>Pearson Edexcel IGCSE</a>{" "}
          and{" "}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-advanced-levels.html" target="_blank" rel="noopener noreferrer" style={{ color: "#6EA8FE", textDecoration: "none" }}>International A Level</a>{" "}
          examinations. Research consistently shows that retrieval practice leads to significantly better exam performance and long-term retention compared to passive revision.
        </p>
        <p style={{ color: "#9CA3AF", fontSize: "0.9rem", lineHeight: 1.8 }}>
          GradeMax organises every Edexcel past paper question by topic so you can target your weak areas precisely. All questions come with official mark schemes so you know exactly what the examiner expects.
        </p>
      </section>

      {/* ── WORRY CATCHER ── */}
      <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", padding: "3.5rem 1.5rem" }}>
        <p style={{ textAlign: "center", fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB", marginBottom: "0.4rem" }}>
          Stressed about exams?
        </p>
        <p style={{ textAlign: "center", color: "#9CA3AF", fontSize: "0.8rem", marginBottom: "1.5rem" }}>
          Click on your worries to catch them.
        </p>
        <LazyWorryCatcher />
      </section>

      {/* ── FAQ ── */}
      <section style={{ padding: "5rem 1.5rem", maxWidth: "660px", margin: "0 auto" }} id="faq">
        <h2 style={{ fontSize: "clamp(1.3rem,3vw,1.9rem)", fontWeight: 800, color: "#E5E7EB", textAlign: "center", marginBottom: "2rem", letterSpacing: "-0.015em" }}>
          Frequently Asked Questions
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {faqs.map((faq, idx) => (
            <details key={idx} style={{ background: "#0B1020", border: "1px solid #1F2937", borderRadius: "0.75rem", overflow: "hidden" }}>
              <summary style={{ padding: "1rem 1.25rem", cursor: "pointer", fontSize: "0.875rem", fontWeight: 600, color: "#E5E7EB", display: "flex", justifyContent: "space-between", alignItems: "center", listStyle: "none", userSelect: "none" }}>
                {faq.q}
                <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#6B7280" strokeWidth={2} style={{ flexShrink: 0, marginLeft: "1rem" }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <p style={{ padding: "0 1.25rem 1rem", fontSize: "0.855rem", color: "#9CA3AF", lineHeight: 1.75 }}>{faq.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ── QUICK LINKS ── */}
      <section style={{ background: "#0B1020", borderTop: "1px solid #1F2937", padding: "2rem 1.5rem" }}>
        <div style={{ maxWidth: "900px", margin: "0 auto", textAlign: "center" }}>
          <p style={{ fontSize: "0.65rem", fontWeight: 700, color: "#4B5563", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "0.875rem" }}>Quick Links</p>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0.25rem 1.25rem" }}>
            {([
              ["/edexcel-past-papers",         "Edexcel Past Papers"],
              ["/edexcel-igcse-past-papers",   "IGCSE Past Papers"],
              ["/edexcel-a-level-past-papers", "A Level Past Papers"],
              ["/edexcel-worksheets",          "Worksheet Generator"],
              ["/subjects",                    "All Subjects"],
            ] as [string, string][]).map(([href, label]) => (
              <Link key={href} href={href} className="quick-link" style={{ fontSize: "0.75rem" }}>{label}</Link>
            ))}
          </div>
        </div>
      </section>

    </main>
  )
}
