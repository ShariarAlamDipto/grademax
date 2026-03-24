"use client"
import { useEffect, useState } from "react"

interface Subject { id: string; name: string; level: string }

const SESSIONS = ["Jan", "May-Jun", "Oct-Nov", "Specimen"]
const YEARS = Array.from({ length: 16 }, (_, i) => String(2024 - i))

const inputStyle: React.CSSProperties = {
  background: "var(--gm-bg)", border: "1px solid var(--gm-border)",
  borderRadius: "0.5rem", padding: "0.5rem 0.75rem",
  color: "var(--gm-text)", fontSize: "0.8rem", width: "100%", outline: "none",
}

export default function ScraperAdminPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subject, setSubject] = useState("")
  const [session, setSession] = useState("")
  const [year, setYear] = useState("")
  const [paperType, setPaperType] = useState("")
  const [running, setRunning] = useState(false)
  const [output, setOutput] = useState<{ ok: boolean; text: string } | null>(null)
  const [isProd, setIsProd] = useState(false)

  useEffect(() => {
    fetch("/api/admin/subjects").then(r => r.json()).then(d => setSubjects(d.subjects || []))
    fetch("/api/admin/scraper")
      .then(r => r.json())
      .then(d => { if (!d.available) setIsProd(true) })
      .catch(() => setIsProd(true))
  }, [])

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!subject) return
    setRunning(true)
    setOutput(null)
    const res = await fetch("/api/admin/scraper", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, session: session || undefined, year: year || undefined, paperType: paperType || undefined }),
    })
    const data = await res.json()
    if (res.ok) {
      setOutput({ ok: true, text: data.stdout || "Done" })
    } else {
      setOutput({ ok: false, text: data.error || data.stderr || "Error" })
    }
    setRunning(false)
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "800px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Scraper</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Trigger the Grademax scraper to download missing papers from Pearson</p>
      </div>

      {isProd && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem 1.25rem", background: "#f9731620", border: "1px solid #f9731640", borderRadius: "0.75rem" }}>
          <p style={{ fontWeight: 600, fontSize: "0.875rem", color: "#f97316", marginBottom: "0.25rem" }}>Production Environment</p>
          <p style={{ fontSize: "0.8rem", color: "var(--gm-text-2)" }}>
            The scraper can only run from your local development environment (Python is not available on Vercel).
            Run the script directly from your machine using the commands below.
          </p>
        </div>
      )}

      <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.5rem", marginBottom: "1.5rem" }}>
        <p style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--gm-text)", marginBottom: "1.25rem" }}>Configure Scraper Run</p>
        <form onSubmit={handleRun}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Subject *</label>
              <select style={inputStyle} value={subject} onChange={e => setSubject(e.target.value)} required>
                <option value="">— All subjects —</option>
                {subjects.map(s => <option key={s.id} value={s.name}>{s.level} · {s.name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Session (optional)</label>
              <select style={inputStyle} value={session} onChange={e => setSession(e.target.value)}>
                <option value="">— All sessions —</option>
                {SESSIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Year (optional)</label>
              <select style={inputStyle} value={year} onChange={e => setYear(e.target.value)}>
                <option value="">— All years —</option>
                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Paper Type (optional)</label>
              <select style={inputStyle} value={paperType} onChange={e => setPaperType(e.target.value)}>
                <option value="">— QP &amp; MS —</option>
                <option value="QP">Question Paper only</option>
                <option value="MS">Mark Scheme only</option>
              </select>
            </div>
          </div>
          <button
            type="submit"
            disabled={running || !subject}
            style={{
              padding: "0.625rem 1.5rem", background: "#a855f7", color: "#fff",
              borderRadius: "0.5rem", border: "none", fontSize: "0.875rem", fontWeight: 600,
              cursor: running || !subject ? "not-allowed" : "pointer",
              opacity: running || !subject ? 0.6 : 1,
            }}
          >
            {running ? "Running…" : "Run Scraper"}
          </button>
        </form>
      </div>

      {output && (
        <div style={{
          background: "var(--gm-surface)", border: `1px solid ${output.ok ? "#22c55e40" : "#ef444440"}`,
          borderRadius: "0.75rem", padding: "1.25rem",
        }}>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, color: output.ok ? "#22c55e" : "#ef4444", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {output.ok ? "Success" : "Error"}
          </p>
          <pre style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "var(--gm-text-2)", whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: "400px", overflowY: "auto" }}>
            {output.text}
          </pre>
        </div>
      )}

      {/* Manual commands */}
      <div style={{ marginTop: "1.5rem" }}>
        <p style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>
          Run Manually
        </p>
        <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1rem" }}>
          <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.5rem" }}>From <code style={{ background: "var(--gm-bg)", padding: "0.1rem 0.3rem", borderRadius: "0.25rem" }}>grademax-scraper/</code> directory:</p>
          {[
            { desc: "Scrape all missing papers for a subject", cmd: "python scrape_missing_papers.py --subject \"ICT\"" },
            { desc: "Scrape specific session", cmd: "python scrape_missing_papers.py --subject \"ICT\" --session \"May-Jun\" --year 2024" },
            { desc: "Scrape ICT only", cmd: "python scrape_ict_only.py" },
          ].map(({ desc, cmd }) => (
            <div key={cmd} style={{ marginBottom: "0.75rem" }}>
              <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginBottom: "0.25rem" }}>{desc}</p>
              <code style={{ display: "block", background: "var(--gm-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", fontSize: "0.75rem", color: "var(--gm-text-2)" }}>
                {cmd}
              </code>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
