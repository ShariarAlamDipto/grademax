"use client"
import { useEffect, useState } from "react"

interface Stats {
  subjects: number; papers: number; papersWithQP: number; papersWithMS: number
  r2Objects: number; tests: number; worksheets: number
  users: { total: number; admins: number; teachers: number; students: number }
}

interface Subject { id: string; name: string; code: string | null; level: string; paperCount: number }

interface CoverageRow {
  id: string; name: string; code: string | null; level: string
  total: number; withQP: number; withMS: number; both: number
  qpPct: number; msPct: number
}

const Bar = ({ value, max, color }: { value: number; max: number; color: string }) => (
  <div style={{ height: "6px", background: "var(--gm-border)", borderRadius: "99px", overflow: "hidden" }}>
    <div style={{ height: "100%", width: `${max > 0 ? Math.round((value / max) * 100) : 0}%`, background: color, borderRadius: "99px", transition: "width 0.4s ease" }} />
  </div>
)

const PctBar = ({ pct, color }: { pct: number; color: string }) => (
  <div style={{ height: "4px", background: "var(--gm-border)", borderRadius: "99px", overflow: "hidden", width: "60px" }}>
    <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "99px" }} />
  </div>
)

type AnalyticsTab = "overview" | "coverage"

export default function AnalyticsAdminPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [coverage, setCoverage] = useState<CoverageRow[]>([])
  const [loading, setLoading] = useState(true)
  const [coverageLoading, setCoverageLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("overview")
  const [coverageSort, setCoverageSort] = useState<"name" | "total" | "qp" | "ms">("total")

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/stats").then(r => { if (!r.ok) throw new Error("stats"); return r.json() }),
      fetch("/api/admin/subjects").then(r => { if (!r.ok) throw new Error("subjects"); return r.json() }),
    ]).then(([s, sub]) => {
      setStats(s)
      setSubjects(sub.subjects || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const loadCoverage = async () => {
    if (coverage.length > 0) return
    setCoverageLoading(true)
    try {
      const res = await fetch("/api/admin/analytics/coverage")
      const data = await res.json()
      setCoverage(data.rows || [])
    } finally {
      setCoverageLoading(false)
    }
  }

  const handleTabChange = (tab: AnalyticsTab) => {
    setActiveTab(tab)
    if (tab === "coverage") loadCoverage()
  }

  const qpPct = stats && stats.papers > 0 ? Math.round((stats.papersWithQP / stats.papers) * 100) : 0
  const msPct = stats && stats.papers > 0 ? Math.round((stats.papersWithMS / stats.papers) * 100) : 0
  const maxPaperCount = subjects.reduce((m, s) => Math.max(m, s.paperCount), 1)
  const topSubjects = [...subjects].sort((a, b) => b.paperCount - a.paperCount).slice(0, 15)

  const sortedCoverage = [...coverage].sort((a, b) => {
    if (coverageSort === "name") return a.name.localeCompare(b.name)
    if (coverageSort === "total") return b.total - a.total
    if (coverageSort === "qp") return b.qpPct - a.qpPct
    return b.msPct - a.msPct
  })

  if (loading) {
    return <div style={{ padding: "2rem", color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</div>
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Analytics</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Content coverage and platform usage</p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--gm-border)", marginBottom: "1.5rem" }}>
        {(["overview", "coverage"] as const).map(tab => (
          <button key={tab} onClick={() => handleTabChange(tab)} style={{
            padding: "0.625rem 1.25rem", fontSize: "0.8rem", fontWeight: activeTab === tab ? 600 : 400,
            color: activeTab === tab ? "var(--gm-text)" : "var(--gm-text-3)",
            borderBottom: activeTab === tab ? "2px solid var(--gm-blue)" : "2px solid transparent",
            background: "transparent", border: "none", cursor: "pointer", textTransform: "capitalize",
          }}>
            {tab === "coverage" ? "Per-Subject Coverage" : "Overview"}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {activeTab === "overview" && (
        <>
          {/* Coverage section */}
          <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Content Coverage</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
            {[
              { label: "Total Subjects", value: stats?.subjects ?? 0, color: "var(--gm-blue)" },
              { label: "Total Papers", value: stats?.papers ?? 0, color: "var(--gm-text)" },
              { label: "R2 Storage Files", value: stats?.r2Objects ?? 0, color: "#f59e0b" },
              { label: "Tests Created", value: stats?.tests ?? 0, color: "#a855f7" },
              { label: "Worksheets Created", value: stats?.worksheets ?? 0, color: "#06b6d4" },
            ].map(s => (
              <div key={s.label} style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.25rem" }}>
                <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.5rem" }}>{s.label}</p>
                <p style={{ fontSize: "2rem", fontWeight: 800, color: s.color }}>{s.value.toLocaleString()}</p>
              </div>
            ))}
          </div>

          {/* QP / MS coverage */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
            {[
              { label: "Question Paper Coverage", pct: qpPct, count: stats?.papersWithQP ?? 0, total: stats?.papers ?? 0, color: "var(--gm-blue)" },
              { label: "Mark Scheme Coverage", pct: msPct, count: stats?.papersWithMS ?? 0, total: stats?.papers ?? 0, color: "#22c55e" },
            ].map(s => (
              <div key={s.label} style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.5rem" }}>
                  <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", fontWeight: 500 }}>{s.label}</p>
                  <p style={{ fontSize: "1.25rem", fontWeight: 800, color: s.color }}>{s.pct}%</p>
                </div>
                <Bar value={s.count} max={s.total} color={s.color} />
                <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.375rem" }}>{s.count.toLocaleString()} of {s.total.toLocaleString()} papers</p>
              </div>
            ))}
          </div>

          {/* Users section */}
          <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Users</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", marginBottom: "2rem" }}>
            {[
              { label: "Total", value: stats?.users.total ?? 0, color: "var(--gm-text)" },
              { label: "Admins", value: stats?.users.admins ?? 0, color: "#ef4444" },
              { label: "Teachers", value: stats?.users.teachers ?? 0, color: "var(--gm-blue)" },
              { label: "Students", value: stats?.users.students ?? 0, color: "#22c55e" },
            ].map(s => (
              <div key={s.label} style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1rem" }}>
                <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.25rem" }}>{s.label}</p>
                <p style={{ fontSize: "1.5rem", fontWeight: 800, color: s.color }}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Subject breakdown */}
          <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Papers per Subject (Top 15)</h2>
          <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden" }}>
            {topSubjects.map((s, i) => (
              <div key={s.id} style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: "0.875rem", alignItems: "center", padding: "0.625rem 1rem", borderBottom: i < topSubjects.length - 1 ? "1px solid var(--gm-border)" : "none" }}>
                <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", width: "1.5rem", textAlign: "right" }}>{i + 1}</span>
                <div>
                  <p style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--gm-text)", marginBottom: "0.25rem" }}>
                    {s.name}
                    <span style={{ marginLeft: "0.5rem", fontSize: "0.65rem", color: "var(--gm-text-3)", background: "var(--gm-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.25rem", padding: "0 0.3rem" }}>{s.level}</span>
                  </p>
                  <Bar value={s.paperCount} max={maxPaperCount} color="var(--gm-blue)" />
                </div>
                <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--gm-text-2)", minWidth: "3rem", textAlign: "right" }}>{s.paperCount}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Per-subject coverage tab */}
      {activeTab === "coverage" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>Sort by:</span>
            {([
              { key: "total", label: "Papers" },
              { key: "name", label: "Name" },
              { key: "qp", label: "QP %" },
              { key: "ms", label: "MS %" },
            ] as const).map(s => (
              <button
                key={s.key}
                onClick={() => setCoverageSort(s.key)}
                style={{
                  padding: "0.25rem 0.625rem", borderRadius: "999px", fontSize: "0.72rem", cursor: "pointer",
                  background: coverageSort === s.key ? "var(--gm-text)" : "var(--gm-surface)",
                  color: coverageSort === s.key ? "var(--gm-bg)" : "var(--gm-text-3)",
                  border: `1px solid ${coverageSort === s.key ? "var(--gm-text)" : "var(--gm-border)"}`,
                  fontWeight: coverageSort === s.key ? 600 : 400,
                }}
              >
                {s.label}
              </button>
            ))}
          </div>

          {coverageLoading ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading coverage data…</div>
          ) : (
            <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 60px 80px 80px 80px", padding: "0.5rem 1rem", borderBottom: "1px solid var(--gm-border)", fontSize: "0.7rem", color: "var(--gm-text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                <span>Subject</span>
                <span style={{ textAlign: "right" }}>Papers</span>
                <span style={{ textAlign: "right" }}>QP %</span>
                <span style={{ textAlign: "right" }}>MS %</span>
                <span style={{ textAlign: "right" }}>Complete</span>
              </div>
              {sortedCoverage.map((row, i) => (
                <div key={row.id} style={{ display: "grid", gridTemplateColumns: "1fr 60px 80px 80px 80px", padding: "0.625rem 1rem", borderBottom: i < sortedCoverage.length - 1 ? "1px solid var(--gm-border)" : "none", alignItems: "center" }}>
                  <div>
                    <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--gm-text)" }}>{row.name}</span>
                    <span style={{ marginLeft: "0.4rem", fontSize: "0.65rem", color: "var(--gm-text-3)", background: "var(--gm-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.25rem", padding: "0 0.3rem" }}>{row.level}</span>
                  </div>
                  <span style={{ fontSize: "0.8rem", color: "var(--gm-text-2)", textAlign: "right" }}>{row.total}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", justifyContent: "flex-end" }}>
                    <span style={{ fontSize: "0.75rem", color: row.qpPct === 100 ? "#22c55e" : row.qpPct > 50 ? "#f59e0b" : "#ef4444", fontWeight: 600 }}>{row.qpPct}%</span>
                    <PctBar pct={row.qpPct} color={row.qpPct === 100 ? "#22c55e" : row.qpPct > 50 ? "#f59e0b" : "#ef4444"} />
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", justifyContent: "flex-end" }}>
                    <span style={{ fontSize: "0.75rem", color: row.msPct === 100 ? "#22c55e" : row.msPct > 50 ? "#f59e0b" : "#ef4444", fontWeight: 600 }}>{row.msPct}%</span>
                    <PctBar pct={row.msPct} color={row.msPct === 100 ? "#22c55e" : row.msPct > 50 ? "#f59e0b" : "#ef4444"} />
                  </div>
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, textAlign: "right", color: row.both === row.total && row.total > 0 ? "#22c55e" : "var(--gm-text-3)" }}>
                    {row.both}/{row.total}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
