"use client"
import { useEffect, useState } from "react"

interface Stats {
  subjects: number; papers: number; papersWithQP: number; papersWithMS: number
  r2Objects: number; users: { total: number; admins: number; teachers: number; students: number }
}

interface Subject { id: string; name: string; code: string | null; level: string; paperCount: number }

const Bar = ({ value, max, color }: { value: number; max: number; color: string }) => (
  <div style={{ height: "6px", background: "var(--gm-border)", borderRadius: "99px", overflow: "hidden" }}>
    <div style={{ height: "100%", width: `${max > 0 ? Math.round((value / max) * 100) : 0}%`, background: color, borderRadius: "99px", transition: "width 0.4s ease" }} />
  </div>
)

export default function AnalyticsAdminPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/stats").then(r => r.json()),
      fetch("/api/admin/subjects").then(r => r.json()),
    ]).then(([s, sub]) => {
      setStats(s)
      setSubjects(sub.subjects || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const qpPct = stats && stats.papers > 0 ? Math.round((stats.papersWithQP / stats.papers) * 100) : 0
  const msPct = stats && stats.papers > 0 ? Math.round((stats.papersWithMS / stats.papers) * 100) : 0
  const maxPaperCount = subjects.reduce((m, s) => Math.max(m, s.paperCount), 1)
  const topSubjects = [...subjects].sort((a, b) => b.paperCount - a.paperCount).slice(0, 15)

  if (loading) {
    return <div style={{ padding: "2rem", color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</div>
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1000px" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Analytics</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Content coverage and platform usage</p>
      </div>

      {/* Coverage section */}
      <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Content Coverage</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        {[
          { label: "Total Subjects", value: stats?.subjects ?? 0, color: "var(--gm-blue)" },
          { label: "Total Papers", value: stats?.papers ?? 0, color: "var(--gm-text)" },
          { label: "R2 Storage Files", value: stats?.r2Objects ?? 0, color: "var(--gm-amber)" },
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
    </div>
  )
}
