"use client"
import { useEffect, useState } from "react"
import Link from "next/link"

interface Stats {
  subjects: number
  papers: number
  papersWithQP: number
  papersWithMS: number
  pages: number
  questionPages: number
  r2Objects: number | null
  users: { total: number; admins: number; teachers: number; students: number }
}

const QUICK_ACTIONS = [
  { href: "/admin/papers", label: "Upload Papers", desc: "Add or update past paper PDFs", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" },
  { href: "/admin/subjects", label: "Manage Subjects", desc: "Add, edit or remove subjects", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" },
  { href: "/admin/users", label: "Manage Users", desc: "View users and assign roles", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" },
  { href: "/admin/scraper", label: "Scraper", desc: "Download missing papers", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" },
  { href: "/admin/tagger", label: "Question Tagger", desc: "Tag and classify questions", icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" },
  { href: "/admin/workbook/verify", label: "Workbook Verification", desc: "Confirm chapter assignments before they reach the book", icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
]

const ARROW = "M5 12h14m-6-6l6 6-6 6"

function percent(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0
}

function formatCount(value: number | null | undefined, loading: boolean): string {
  if (loading || value === null || value === undefined) return "—"
  return value.toLocaleString("en-GB")
}

/** Half-circle gauge, 0–100. The arc length of a r=80 semicircle is π·80. */
function Gauge({ value, label }: { value: number; label: string }) {
  const arc = Math.PI * 80
  const filled = (Math.min(Math.max(value, 0), 100) / 100) * arc
  return (
    <div className="ad-gauge" role="img" aria-label={`${label}: ${value}%`}>
      <svg viewBox="0 0 200 112">
        <path d="M20 100a80 80 0 01160 0" fill="none" stroke="var(--ad-accent-soft)" strokeWidth="14" strokeLinecap="round" />
        <path d="M20 100a80 80 0 01160 0" fill="none" stroke="var(--ad-accent)" strokeWidth="14" strokeLinecap="round" strokeDasharray={`${filled} ${arc}`} />
      </svg>
      <div className="ad-gauge-value">
        <strong>{value}%</strong>
        <span>{label}</span>
      </div>
    </div>
  )
}

function SeeDetails({ href }: { href: string }) {
  return (
    <Link href={href} className="ad-card-foot">
      See details
      <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round" d={ARROW} />
      </svg>
    </Link>
  )
}

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [r2Count, setR2Count] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    fetch("/api/admin/stats")
      .then(r => {
        if (!r.ok) throw new Error(`stats ${r.status}`)
        return r.json()
      })
      .then((d: Stats) => { setStats(d); setLoading(false) })
      .catch(() => { setFailed(true); setLoading(false) })
    // R2 count is slow (full bucket listing) — loaded separately so the
    // dashboard never blocks on it.
    fetch("/api/admin/stats/r2")
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && typeof d.r2Objects === "number") setR2Count(d.r2Objects) })
      .catch(() => {})
  }, [])

  const papers = stats?.papers ?? 0
  const qpPct = percent(stats?.papersWithQP ?? 0, papers)
  const msPct = percent(stats?.papersWithMS ?? 0, papers)
  const questionPct = percent(stats?.questionPages ?? 0, stats?.pages ?? 0)
  const users = stats?.users
  const userBars = users
    ? [users.students, users.teachers, users.admins].map(n => Math.max(percent(n, Math.max(users.students, users.teachers, users.admins, 1)), 6))
    : [0, 0, 0]

  return (
    <div className="ad-page">
      <div className="ad-head">
        <div>
          <h1 className="ad-title">Dashboard</h1>
          <p className="ad-lead">Papers, coverage and people across GradeMax</p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <Link href="/admin/analytics" className="ad-btn">Analytics</Link>
          <Link href="/admin/papers" className="ad-btn ad-btn-dark">+ Upload papers</Link>
        </div>
      </div>

      {failed ? (
        <p className="ad-note" role="alert" style={{ marginBottom: "1rem" }}>
          The overview figures could not be loaded. Reload the page to try again.
        </p>
      ) : null}

      <div className="ad-row ad-row-3">
        <section className="ad-card">
          <div className="ad-card-body">
            <p className="ad-card-label">Paper library</p>
            <p className="ad-figure">{formatCount(stats?.papers, loading)}<small>papers</small></p>
            <p className="ad-note">{formatCount(stats?.subjects, loading)} subjects · {formatCount(r2Count, false)} files in storage</p>
            <div className="ad-meter-row"><span>Question papers</span><b>{loading ? "—" : `${qpPct}%`}</b></div>
            <div className="ad-meter"><i style={{ width: `${qpPct}%` }} /></div>
            <div className="ad-meter-row"><span>Mark schemes</span><b>{loading ? "—" : `${msPct}%`}</b></div>
            <div className="ad-meter"><i style={{ width: `${msPct}%` }} /></div>
          </div>
          <SeeDetails href="/admin/papers" />
        </section>

        <section className="ad-card">
          <div className="ad-card-body">
            <p className="ad-card-label">Tool questions</p>
            <div className="ad-split">
              <div>
                <p className="ad-figure">{formatCount(stats?.questionPages, loading)}</p>
                <p className="ad-note">
                  of {formatCount(stats?.pages, loading)} pages{" "}
                  <span className="ad-chip">{loading ? "—" : `${questionPct}%`}</span>
                </p>
              </div>
              <div className="ad-bars" aria-hidden>
                {[questionPct, qpPct, msPct].map((h, i) => (
                  <span key={i} className="ad-bar"><i style={{ height: `${Math.max(h, 6)}%` }} /></span>
                ))}
              </div>
            </div>
          </div>
          <SeeDetails href="/admin/tagger" />
        </section>

        <section className="ad-card">
          <div className="ad-card-body">
            <p className="ad-card-label">People</p>
            <div className="ad-split">
              <div>
                <p className="ad-figure">{formatCount(users?.total, loading)}</p>
                <p className="ad-note">
                  {formatCount(users?.students, loading)} students · {formatCount(users?.teachers, loading)} teachers · {formatCount(users?.admins, loading)} admins
                </p>
              </div>
              <div className="ad-bars" aria-hidden>
                {userBars.map((h, i) => (
                  <span key={i} className="ad-bar"><i style={{ height: `${h}%` }} /></span>
                ))}
              </div>
            </div>
          </div>
          <SeeDetails href="/admin/users" />
        </section>
      </div>

      <div className="ad-row ad-row-2">
        <section className="ad-card">
          <div className="ad-card-body">
            <h2 className="ad-section-title" style={{ marginTop: 0 }}>Quick actions</h2>
            <div className="ad-actions">
              {QUICK_ACTIONS.map(action => (
                <Link key={action.href} href={action.href} className="ad-action">
                  <span className="ad-action-icon">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d={action.icon} />
                    </svg>
                  </span>
                  <span>
                    <b>{action.label}</b>
                    <span>{action.desc}</span>
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="ad-card">
          <div className="ad-card-body">
            <p className="ad-card-label">Coverage</p>
            <Gauge value={loading ? 0 : msPct} label="papers with a mark scheme" />
            <div className="ad-legend">
              <div><span><i />Question papers</span><span>{formatCount(stats?.papersWithQP, loading)}</span></div>
              <div><span><i data-soft />Mark schemes</span><span>{formatCount(stats?.papersWithMS, loading)}</span></div>
            </div>
          </div>
          <SeeDetails href="/admin/analytics" />
        </section>
      </div>
    </div>
  )
}
