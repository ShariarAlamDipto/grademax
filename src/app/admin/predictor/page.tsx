"use client"
import { Fragment, useEffect, useMemo, useState } from "react"

interface TargetInfo { label: string; session: string; year: number }
interface Evidence { q_id: string; year: number; marks: number | null; context: string }
interface Slot {
  slot: number
  topic_name: string
  marks: number
  command_words: string[]
  difficulty: string
  skills: string[]
  confidence: number
  confidence_band: "high" | "medium" | "low"
  rationale: string
  evidence: Evidence[]
  style_reference?: { context_tag?: string }
}
interface PaperBlueprint {
  paper: string
  paper_name: string
  total_marks: number
  question_count: number
  predicted_marks: number
  slots: Slot[]
}
interface Blueprint {
  subject_code: string
  subject_name: string
  target: TargetInfo
  papers: Record<string, PaperBlueprint>
}
interface IndexEntry {
  code: string
  name: string
  target: TargetInfo
  dir: string
  papers: string[]
  artifacts: {
    report?: string
    blueprint: string
    paper: Record<string, string>
    markscheme: Record<string, string>
  }
  summary: { paper: string; name: string; question_count: number; predicted_marks: number; total_marks: number; high_conf: number }[]
  published_at: string
}

const BASE = "/predictor/"
const BAND_COLOR: Record<string, string> = { high: "#22c55e", medium: "#f59e0b", low: "#ef4444" }

const card: React.CSSProperties = {
  background: "var(--gm-surface)", border: "1px solid var(--gm-border)",
  borderRadius: "0.75rem", padding: "1.25rem", marginBottom: "1rem",
}
const btn: React.CSSProperties = {
  display: "inline-block", padding: "0.45rem 0.85rem", borderRadius: "0.5rem",
  background: "var(--gm-blue)", color: "#fff", fontSize: "0.8rem", fontWeight: 600,
  textDecoration: "none", marginRight: "0.5rem",
}
const btnGhost: React.CSSProperties = {
  ...btn, background: "transparent", color: "var(--gm-text)", border: "1px solid var(--gm-border)",
}

export default function PredictorAdminPage() {
  const [index, setIndex] = useState<IndexEntry[]>([])
  const [code, setCode] = useState<string>("")
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null)
  const [activePaper, setActivePaper] = useState<string>("")
  const [openRow, setOpenRow] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(BASE + "index.json")
      .then(r => (r.ok ? r.json() : { subjects: [] }))
      .then(d => {
        const subs: IndexEntry[] = d.subjects || []
        setIndex(subs)
        if (subs[0]) setCode(subs[0].code)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const entry = useMemo(() => index.find(s => s.code === code), [index, code])

  useEffect(() => {
    if (!entry) { setBlueprint(null); return }
    fetch(BASE + entry.artifacts.blueprint)
      .then(r => r.json())
      .then((b: Blueprint) => {
        setBlueprint(b)
        setActivePaper(Object.keys(b.papers)[0] || "")
      })
      .catch(() => setBlueprint(null))
  }, [entry])

  const paper = blueprint && activePaper ? blueprint.papers[activePaper] : null

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>
          Question Pattern Predictor
        </h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>
          Data-driven blueprints and AI-written practice papers from historical question patterns.
        </p>
      </div>

      {loading && <p style={{ color: "var(--gm-text-3)" }}>Loading…</p>}

      {!loading && index.length === 0 && (
        <div style={card}>
          <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>No predictions published yet.</p>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.85rem" }}>
            Generate one from the repo with:{" "}
            <code style={{ background: "var(--gm-bg)", padding: "0 0.3rem", borderRadius: "0.25rem" }}>
              python scripts/predictor/run_all.py --subject 4PM1
            </code>
          </p>
        </div>
      )}

      {!loading && index.length > 0 && (
        <>
          {/* Subject selector */}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            {index.map(s => (
              <button key={s.code} onClick={() => setCode(s.code)}
                style={{
                  padding: "0.5rem 1rem", borderRadius: "0.5rem", fontSize: "0.85rem", fontWeight: 600,
                  cursor: "pointer", border: "1px solid var(--gm-border)",
                  background: s.code === code ? "var(--gm-blue)" : "transparent",
                  color: s.code === code ? "#fff" : "var(--gm-text)",
                }}>
                {s.name} ({s.code})
              </button>
            ))}
          </div>

          {entry && (
            <div style={card}>
              <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", marginBottom: "0.4rem" }}>
                Target: <strong style={{ color: "var(--gm-text)" }}>{entry.target.label}</strong>
                {" · "}published {entry.published_at?.slice(0, 10)}
              </p>
              <div style={{ marginTop: "0.6rem" }}>
                {entry.artifacts.report && (
                  <a style={btnGhost} href={BASE + entry.artifacts.report} target="_blank" rel="noreferrer">📊 Pattern report</a>
                )}
                {entry.papers.map(pid => (
                  <span key={pid}>
                    <a style={btn} href={BASE + (entry.artifacts.paper[pid] || "")} target="_blank" rel="noreferrer">📝 Paper {pid}</a>
                    <a style={btnGhost} href={BASE + (entry.artifacts.markscheme[pid] || "")} target="_blank" rel="noreferrer">✓ MS {pid}</a>
                  </span>
                ))}
              </div>
              <p style={{ marginTop: "0.75rem", fontSize: "0.7rem", color: "var(--gm-text-3)" }}>
                ⚠️ AI-predicted practice material — not official Pearson/Edexcel papers.
              </p>
            </div>
          )}

          {/* Paper tabs */}
          {blueprint && (
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
              {Object.values(blueprint.papers).map(p => (
                <button key={p.paper} onClick={() => setActivePaper(p.paper)}
                  style={{
                    padding: "0.4rem 0.9rem", borderRadius: "0.5rem", fontSize: "0.8rem", fontWeight: 600,
                    cursor: "pointer", border: "1px solid var(--gm-border)",
                    background: p.paper === activePaper ? "var(--gm-surface-2, rgba(255,255,255,0.06))" : "transparent",
                    color: "var(--gm-text)",
                  }}>
                  {p.paper_name} · {p.predicted_marks}/{p.total_marks}m · {p.question_count}Q
                </button>
              ))}
            </div>
          )}

          {/* Blueprint table */}
          {paper && (
            <div style={card}>
              <h2 style={{ fontSize: "1.05rem", fontWeight: 700, marginBottom: "0.75rem" }}>
                {paper.paper_name} blueprint
              </h2>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "var(--gm-text-3)" }}>
                      <th style={th}>Q</th><th style={th}>Predicted topic</th><th style={th}>Marks</th>
                      <th style={th}>Difficulty</th><th style={th}>Confidence</th><th style={th}>Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paper.slots.map(s => {
                      const key = `${paper.paper}-${s.slot}`
                      const open = openRow === key
                      return (
                        <Fragment key={key}>
                          <tr style={{ borderTop: "1px solid var(--gm-border)", cursor: "pointer" }}
                            onClick={() => setOpenRow(open ? null : key)}>
                            <td style={td}>{s.slot}</td>
                            <td style={{ ...td, fontWeight: 600 }}>{s.topic_name}</td>
                            <td style={td}>{s.marks}</td>
                            <td style={td}>{s.difficulty}</td>
                            <td style={td}>
                              <span style={{
                                display: "inline-block", padding: "0.1rem 0.5rem", borderRadius: "1rem",
                                fontSize: "0.7rem", fontWeight: 700, color: "#fff",
                                background: BAND_COLOR[s.confidence_band] || "#888",
                              }}>{s.confidence_band} {Math.round(s.confidence * 100)}%</span>
                            </td>
                            <td style={{ ...td, color: "var(--gm-text-3)", maxWidth: 280 }}>
                              {open ? "▾" : "▸"} {s.rationale.slice(0, 60)}{s.rationale.length > 60 ? "…" : ""}
                            </td>
                          </tr>
                          {open && (
                            <tr>
                              <td colSpan={6} style={{ ...td, background: "var(--gm-bg)" }}>
                                <div style={{ fontSize: "0.78rem", color: "var(--gm-text-2)", lineHeight: 1.6 }}>
                                  <div><strong>Rationale:</strong> {s.rationale}</div>
                                  {s.skills?.length > 0 && <div><strong>Skills:</strong> {s.skills.join(", ")}</div>}
                                  {s.command_words?.length > 0 && <div><strong>Command words:</strong> {s.command_words.join(", ")}</div>}
                                  {s.style_reference?.context_tag && <div><strong>Style ref:</strong> {s.style_reference.context_tag}</div>}
                                  {s.evidence?.length > 0 && (
                                    <div><strong>Evidence:</strong> {s.evidence.map(e => `${e.year} (${e.context || e.q_id})`).join(" · ")}</div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: "0.4rem 0.5rem", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.04em" }
const td: React.CSSProperties = { padding: "0.5rem 0.5rem", verticalAlign: "top" }
