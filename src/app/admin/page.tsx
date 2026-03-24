"use client"
import { useEffect, useState } from "react"
import Link from "next/link"

interface Stats {
  subjects: number
  papers: number
  papersWithQP: number
  papersWithMS: number
  r2Objects: number
  users: { total: number; admins: number; teachers: number; students: number }
}

const QUICK_ACTIONS = [
  { href: "/admin/papers", label: "Upload Papers", desc: "Add or update past paper PDFs", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12", color: "var(--gm-blue)" },
  { href: "/admin/subjects", label: "Manage Subjects", desc: "Add, edit or remove subjects", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253", color: "var(--gm-amber)" },
  { href: "/admin/users", label: "Manage Users", desc: "View users and assign roles", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z", color: "#22c55e" },
  { href: "/admin/scraper", label: "Scraper", desc: "Download missing papers", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4", color: "#a855f7" },
  { href: "/admin/analytics", label: "Analytics", desc: "Usage and coverage stats", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z", color: "#f97316" },
  { href: "/admin/tagger", label: "Question Tagger", desc: "Tag and classify questions", icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z", color: "#ec4899" },
]

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/admin/stats")
      .then(r => r.json())
      .then(d => { setStats(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const qpPct = stats && stats.papers > 0 ? Math.round((stats.papersWithQP / stats.papers) * 100) : 0
  const msPct = stats && stats.papers > 0 ? Math.round((stats.papersWithMS / stats.papers) * 100) : 0

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Overview</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>GradeMax Admin Portal</p>
      </div>

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        {[
          { label: "Subjects", value: stats?.subjects, color: "var(--gm-blue)" },
          { label: "Papers", value: stats?.papers, color: "var(--gm-text)" },
          { label: "QP Coverage", value: loading ? "—" : `${qpPct}%`, color: "#22c55e", sub: `${stats?.papersWithQP ?? 0} papers` },
          { label: "MS Coverage", value: loading ? "—" : `${msPct}%`, color: "#f97316", sub: `${stats?.papersWithMS ?? 0} papers` },
          { label: "R2 Files", value: stats?.r2Objects, color: "var(--gm-amber)" },
          { label: "Users", value: stats?.users.total, color: "#a855f7", sub: `${stats?.users.admins ?? 0} admin · ${stats?.users.teachers ?? 0} teacher` },
        ].map(item => (
          <div key={item.label} style={{
            background: "var(--gm-surface)",
            border: "1px solid var(--gm-border)",
            borderRadius: "0.75rem",
            padding: "1.25rem",
          }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.5rem" }}>{item.label}</p>
            <p style={{ fontSize: "1.75rem", fontWeight: 800, color: item.color, lineHeight: 1 }}>
              {loading ? "—" : (item.value ?? "—")}
            </p>
            {item.sub && <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.25rem" }}>{item.sub}</p>}
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <h2 style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.75rem" }}>Quick Actions</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.75rem" }}>
        {QUICK_ACTIONS.map(action => (
          <Link key={action.href} href={action.href} style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "1rem",
            background: "var(--gm-surface)",
            border: "1px solid var(--gm-border)",
            borderRadius: "0.75rem",
            padding: "1.25rem",
            textDecoration: "none",
            transition: "border-color 0.15s ease",
          }}>
            <div style={{
              width: "2.25rem",
              height: "2.25rem",
              borderRadius: "0.5rem",
              background: `${action.color}18`,
              border: `1px solid ${action.color}30`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}>
              <svg style={{ width: "1.1rem", height: "1.1rem", color: action.color }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d={action.icon} />
              </svg>
            </div>
            <div>
              <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--gm-text)", marginBottom: "0.2rem" }}>{action.label}</p>
              <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>{action.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
