import Link from "next/link"
import { getHubData } from "@/lib/hub-index"
import type { Board, Level } from "@/lib/subjects"

interface PastPaperCatalogProps {
  /** Restrict to one level; omit for all subjects (top-level hub). */
  level?: Level
  /** Human label used in headings, e.g. "IGCSE", "A Level", "Edexcel". */
  levelLabel: string
  /** Exam board whose subjects to list. Defaults to Edexcel (original hubs). */
  board?: Board
}

const headingStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 700,
  color: "var(--gm-text)",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  marginBottom: "1rem",
}

/**
 * Shared server component for the head-term hub pages. Renders (1) a paper-code →
 * subject reference table — genuine unique content that directly serves code
 * queries like "wme01 past papers" — and (2) a by-subject/by-year link index that
 * makes the full /past-papers catalog reachable from each hub. All links are
 * filtered against the DB index in getHubData(), so none point at empty pages.
 */
export default async function PastPaperCatalog({ level, levelLabel, board = "edexcel" }: PastPaperCatalogProps) {
  const { subjects, codeRefs } = await getHubData(level, board)
  if (subjects.length === 0) return null

  const boardName = board === "cambridge" ? "Cambridge" : "Edexcel"
  // Cambridge calls them syllabus codes (0620, 9702); Edexcel paper codes (4PH1).
  const codeNoun = board === "cambridge" ? "syllabus code" : "paper code"
  // "Edexcel IGCSE", or just the board name when no level qualifier is given.
  const scopeLabel = [boardName, levelLabel].filter(Boolean).join(" ")

  return (
    <>
      {codeRefs.length > 0 && (
        <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid var(--gm-border)" }}>
          <h2 style={headingStyle}>{scopeLabel} {board === "cambridge" ? "Syllabus Codes" : "Paper Codes"}</h2>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.85rem", lineHeight: 1.6, maxWidth: "640px", marginBottom: "1.25rem" }}>
            Every {boardName} qualification has a {codeNoun} that students often search by. Here is what each
            {" "}{scopeLabel} {codeNoun} stands for — tap any code to open its past papers.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.5rem" }}>
            {codeRefs.map((ref) => (
              <Link
                key={ref.code}
                href={`/past-papers/${ref.slug}`}
                className="gm-card"
                style={{ display: "flex", alignItems: "center", gap: "0.625rem", background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.625rem", padding: "0.625rem 0.875rem", textDecoration: "none" }}
              >
                <span style={{ fontSize: "0.72rem", fontWeight: 700, fontFamily: "monospace", color: "var(--gm-blue)", background: "var(--gm-blue-bg)", border: "1px solid var(--gm-blue-ring)", borderRadius: "5px", padding: "0.2rem 0.45rem", flexShrink: 0 }}>
                  {ref.code}
                </span>
                <span style={{ fontSize: "0.8rem", color: "var(--gm-text-2)" }}>{ref.subjectLabel} past papers</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section style={{ marginBottom: "3rem", paddingTop: "2rem", borderTop: "1px solid var(--gm-border)" }}>
        <h2 style={headingStyle}>Browse Every {scopeLabel} Subject by Year</h2>
        <p style={{ color: "var(--gm-text-2)", fontSize: "0.85rem", lineHeight: 1.6, maxWidth: "640px", marginBottom: "1.5rem" }}>
          Pick a subject to see every session, or jump straight to a year. Each session page has the
          question papers and official mark schemes as free PDFs.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {subjects.map((s) => (
            <div key={`${s.level}-${s.slug}`}>
              <Link href={`/past-papers/${s.slug}`} className="gm-link" style={{ fontSize: "0.9rem", fontWeight: 700 }}>
                {s.name} Past Papers →
              </Link>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.5rem" }}>
                {s.years.map((year) => (
                  <Link key={year} href={`/past-papers/${s.slug}/${year}`} className="topic-pill" style={{ fontSize: "0.72rem" }}>
                    {year}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
