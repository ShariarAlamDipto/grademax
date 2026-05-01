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

interface UsageData {
  totals: Record<string, number>
  uniqueUsers: Record<string, number>
  worksheetBySubject: Record<string, Record<string, number>>
  testBuilderBySubject: Record<string, Record<string, number>>
  daily: { date: string; [key: string]: number | string }[]
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

const UsageStat = ({ label, total, unique, color }: { label: string; total: number; unique: number; color: string }) => (
  <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.25rem" }}>
    <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.5rem" }}>{label}</p>
    <p style={{ fontSize: "2rem", fontWeight: 800, color, lineHeight: 1 }}>{total.toLocaleString()}</p>
    <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.3rem" }}>{unique.toLocaleString()} unique users</p>
  </div>
)

type AnalyticsTab = "overview" | "coverage" | "usage"

export default function AnalyticsAdminPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [coverage, setCoverage] = useState<CoverageRow[]>([])
  const [usage, setUsage] = useState<UsageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [coverageLoading, setCoverageLoading] = useState(false)
  const [usageLoading, setUsageLoading] = useState(false)
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

  const loadUsage = async () => {
    if (usage) return
    setUsageLoading(true)
    try {
      const res = await fetch("/api/admin/analytics/usage")
      const data = await res.json()
      setUsage(data)
    } finally {
      setUsageLoading(false)
    }
  }

  const handleTabChange = (tab: AnalyticsTab) => {
    setActiveTab(tab)
    if (tab === "coverage") loadCoverage()
    if (tab === "usage") loadUsage()
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
        {(["overview", "coverage", "usage"] as const).map(tab => (
          <button key={tab} onClick={() => handleTabChange(tab)} style={{
            padding: "0.625rem 1.25rem", fontSize: "0.8rem", fontWeight: activeTab === tab ? 600 : 400,
            color: activeTab === tab ? "var(--gm-text)" : "var(--gm-text-3)",
            borderBottom: activeTab === tab ? "2px solid var(--gm-blue)" : "2px solid transparent",
            background: "transparent", border: "none", cursor: "pointer", textTransform: "capitalize",
          }}>
            {tab === "coverage" ? "Per-Subject Coverage" : tab === "usage" ? "Feature Usage" : "Overview"}
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

      {/* Feature Usage tab */}
      {activeTab === "usage" && (
        <div>
          {usageLoading ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading usage data…</div>
          ) : !usage ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>No data yet.</div>
          ) : (
            <>
              {/* Lectures */}
              <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Lectures</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                <UsageStat label="Tab Views" total={usage.totals.lecture_view ?? 0} unique={usage.uniqueUsers.lecture_view ?? 0} color="var(--gm-blue)" />
                <UsageStat label="File Downloads" total={usage.totals.lecture_download ?? 0} unique={usage.uniqueUsers.lecture_download ?? 0} color="#06b6d4" />
              </div>

              {/* Worksheets */}
              <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Worksheet Generator</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1.25rem" }}>
                <UsageStat label="Worksheets Generated" total={usage.totals.worksheet_generate ?? 0} unique={usage.uniqueUsers.worksheet_generate ?? 0} color="#22c55e" />
                <UsageStat label="Worksheets Downloaded" total={usage.totals.worksheet_download ?? 0} unique={usage.uniqueUsers.worksheet_download ?? 0} color="#a855f7" />
              </div>

              {/* Worksheet by subject */}
              {Object.keys(usage.worksheetBySubject).length > 0 && (
                <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden", marginBottom: "2rem" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", padding: "0.5rem 1rem", borderBottom: "1px solid var(--gm-border)", fontSize: "0.7rem", color: "var(--gm-text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    <span>Subject</span>
                    <span style={{ textAlign: "right" }}>Generated</span>
                    <span style={{ textAlign: "right" }}>Downloaded</span>
                  </div>
                  {Object.entries(usage.worksheetBySubject).map(([name, counts], i, arr) => (
                    <div key={name} style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", padding: "0.625rem 1rem", borderBottom: i < arr.length - 1 ? "1px solid var(--gm-border)" : "none", alignItems: "center" }}>
                      <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "var(--gm-text)" }}>{name}</span>
                      <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#22c55e", textAlign: "right" }}>{counts.worksheet_generate ?? 0}</span>
                      <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#a855f7", textAlign: "right" }}>{counts.worksheet_download ?? 0}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Test Builder */}
              <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Test Builder</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1.25rem" }}>
                <UsageStat label="Sessions Started" total={usage.totals.test_builder_session ?? 0} unique={usage.uniqueUsers.test_builder_session ?? 0} color="#f59e0b" />
                <UsageStat label="Tests Downloaded" total={usage.totals.test_builder_download ?? 0} unique={usage.uniqueUsers.test_builder_download ?? 0} color="#ef4444" />
              </div>

              {/* Test Builder by subject */}
              {Object.keys(usage.testBuilderBySubject).length > 0 && (
                <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden", marginBottom: "2rem" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", padding: "0.5rem 1rem", borderBottom: "1px solid var(--gm-border)", fontSize: "0.7rem", color: "var(--gm-text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    <span>Subject</span>
                    <span style={{ textAlign: "right" }}>Sessions</span>
                    <span style={{ textAlign: "right" }}>Downloads</span>
                  </div>
                  {Object.entries(usage.testBuilderBySubject).map(([name, counts], i, arr) => (
                    <div key={name} style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", padding: "0.625rem 1rem", borderBottom: i < arr.length - 1 ? "1px solid var(--gm-border)" : "none", alignItems: "center" }}>
                      <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "var(--gm-text)" }}>{name}</span>
                      <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#f59e0b", textAlign: "right" }}>{counts.test_builder_session ?? 0}</span>
                      <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#ef4444", textAlign: "right" }}>{counts.test_builder_download ?? 0}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* 30-day activity */}
              {usage.daily.length > 0 && (
                <>
                  <h2 style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Last 30 Days — Daily Activity</h2>
                  <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--gm-border)" }}>
                          {["Date", "Lec Views", "Lec DL", "WS Gen", "WS DL", "TB Sessions", "TB DL"].map(h => (
                            <th key={h} style={{ padding: "0.5rem 0.75rem", textAlign: h === "Date" ? "left" : "right", color: "var(--gm-text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[...usage.daily].reverse().map((row, i) => (
                          <tr key={row.date as string} style={{ borderBottom: i < usage.daily.length - 1 ? "1px solid var(--gm-border)" : "none" }}>
                            <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text-2)", fontWeight: 500 }}>{row.date}</td>
                            {["lecture_view", "lecture_download", "worksheet_generate", "worksheet_download", "test_builder_session", "test_builder_download"].map(f => (
                              <td key={f} style={{ padding: "0.5rem 0.75rem", textAlign: "right", color: (row[f] as number) > 0 ? "var(--gm-text)" : "var(--gm-text-3)", fontWeight: (row[f] as number) > 0 ? 600 : 400 }}>
                                {(row[f] as number) || 0}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
