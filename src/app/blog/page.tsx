import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Revision Guides & Exam Tips | GradeMax Blog",
  description: "Free revision guides, exam strategies, and study tips for Edexcel IGCSE and A Level students. Learn how to get A* grades in Physics, Maths, Chemistry, Biology and more.",
  alternates: { canonical: "https://grademax.me/blog" },
  openGraph: {
    title: "Revision Guides & Exam Tips | GradeMax Blog",
    description: "Free revision guides and exam strategies for Edexcel IGCSE and A Level students.",
    url: "https://grademax.me/blog",
    siteName: "GradeMax",
    type: "website",
  },
}

const articles = [
  {
    slug: "how-to-use-past-papers-effectively",
    title: "How to Use Past Papers Effectively for IGCSE & A Level",
    excerpt: "Most students use past papers wrong. Here is the exact method that maximises your mark-per-hour when practising with Edexcel past papers.",
    tag: "Study Strategy",
    tagColor: "#6EA8FE",
    date: "2025-06-10",
  },
  {
    slug: "edexcel-igcse-physics-revision-guide",
    title: "Edexcel IGCSE Physics (4PH1) Complete Revision Guide",
    excerpt: "Topic-by-topic breakdown of the Edexcel IGCSE Physics syllabus with the most common exam questions, mark scheme tips, and common mistakes to avoid.",
    tag: "Physics",
    tagColor: "#F97316",
    date: "2025-06-05",
  },
  {
    slug: "edexcel-igcse-maths-a-revision-guide",
    title: "Edexcel IGCSE Maths A (4MA1) — How to Get a Grade 9",
    excerpt: "The key topics that decide your Maths A grade, with worked examples from real Edexcel past papers and time-saving techniques for Paper 1 and Paper 2.",
    tag: "Mathematics",
    tagColor: "#6EA8FE",
    date: "2025-05-28",
  },
  {
    slug: "how-to-get-a-star-igcse-chemistry",
    title: "How to Get A* in Edexcel IGCSE Chemistry (4CH1)",
    excerpt: "The highest-mark topics in IGCSE Chemistry, how to write perfect six-mark answers, and which past paper questions appear every single year.",
    tag: "Chemistry",
    tagColor: "#34D399",
    date: "2025-05-20",
  },
  {
    slug: "pure-maths-1-wma11-revision-tips",
    title: "Pure Mathematics 1 (WMA11) — A Level Revision Tips",
    excerpt: "Edexcel International A Level Pure Maths 1 covers a huge amount. Here is how to prioritise topics, score full marks on proof questions, and avoid dropping silly marks.",
    tag: "A Level Maths",
    tagColor: "#A78BFA",
    date: "2025-05-12",
  },
  {
    slug: "edexcel-vs-cambridge-igcse-differences",
    title: "Edexcel IGCSE vs Cambridge IGCSE: What is the Difference?",
    excerpt: "Choosing between Pearson Edexcel and Cambridge for your IGCSEs? This guide compares the syllabus, grading, exam structure, and which past papers to use for each.",
    tag: "Exam Boards",
    tagColor: "#F59E0B",
    date: "2025-05-01",
  },
  {
    slug: "igcse-biology-paper-2-tips",
    title: "Edexcel IGCSE Biology Paper 2 — Question Types & How to Score Full Marks",
    excerpt: "Paper 2 Biology questions follow predictable patterns. Learn exactly what examiners look for, which command words trigger which answer structure, and how to maximise marks quickly.",
    tag: "Biology",
    tagColor: "#34D399",
    date: "2025-04-22",
  },
  {
    slug: "revision-timetable-igcse-a-level",
    title: "How to Build a Revision Timetable That Actually Works",
    excerpt: "A step-by-step approach to building a realistic, subject-balanced revision timetable for IGCSE and A Level exams — with a downloadable template.",
    tag: "Study Strategy",
    tagColor: "#6EA8FE",
    date: "2025-04-10",
  },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })
}

export default function BlogPage() {
  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <div style={{ maxWidth: "900px", margin: "0 auto", padding: "3.5rem 1.5rem 5rem" }}>

        {/* Header */}
        <div style={{ marginBottom: "3rem" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.5rem" }}>
            Revision Guides & Exam Tips
          </p>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.6rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.03em", lineHeight: 1.1, marginBottom: "1rem" }}>
            GradeMax Blog
          </h1>
          <p style={{ color: "var(--gm-text-2)", fontSize: "1rem", lineHeight: 1.6, maxWidth: "540px" }}>
            Free revision guides, exam strategies, and study tips written for Edexcel IGCSE and A Level students aiming for top grades.
          </p>
        </div>

        {/* Article grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "1.25rem" }}>
          {articles.map(article => (
            <Link
              key={article.slug}
              href={`/blog/${article.slug}`}
              style={{ textDecoration: "none" }}
            >
              <article
                style={{
                  border: "1px solid var(--gm-border)",
                  borderRadius: "1rem",
                  padding: "1.5rem",
                  background: "var(--gm-surface)",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem",
                  transition: "border-color 0.15s, box-shadow 0.15s",
                  cursor: "pointer",
                }}
                className="card-hover"
              >
                <span style={{
                  display: "inline-block",
                  padding: "0.2rem 0.6rem",
                  borderRadius: "999px",
                  fontSize: "0.68rem",
                  fontWeight: 700,
                  letterSpacing: "0.05em",
                  background: `${article.tagColor}18`,
                  color: article.tagColor,
                  alignSelf: "flex-start",
                }}>
                  {article.tag}
                </span>
                <h2 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--gm-text)", lineHeight: 1.4, margin: 0 }}>
                  {article.title}
                </h2>
                <p style={{ fontSize: "0.82rem", color: "var(--gm-text-2)", lineHeight: 1.6, margin: 0, flex: 1 }}>
                  {article.excerpt}
                </p>
                <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", margin: 0 }}>
                  {formatDate(article.date)}
                </p>
              </article>
            </Link>
          ))}
        </div>

        {/* CTA */}
        <div style={{
          marginTop: "3.5rem",
          padding: "2rem",
          borderRadius: "1rem",
          border: "1px solid var(--gm-border)",
          background: "var(--gm-surface)",
          textAlign: "center",
        }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.5rem" }}>
            Ready to start practising?
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--gm-text-2)", marginBottom: "1.25rem" }}>
            Use GradeMax to generate a custom worksheet from real Edexcel past paper questions — free, in seconds.
          </p>
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/generate" className="btn-beacon">
              Generate Worksheet
            </Link>
            <Link href="/past-papers" className="btn-ghost-amber">
              Browse Past Papers
            </Link>
          </div>
        </div>

      </div>
    </main>
  )
}
