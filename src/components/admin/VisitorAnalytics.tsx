"use client"
import { useCallback, useEffect, useState } from "react"
import { AreaChart, Area, BarChart, Bar as RBar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"

interface DailyRow { day: string; views: number; visitors: number; new_visitors: number; signed_in: number; signups: number }
interface VisitorData {
  days: number
  timezone: string
  totals: {
    live: number; today: number; yesterday: number; last7: number
    visitors: number; new_visitors: number; views: number; signups: number
    tracking_since: string | null
  }
  daily: DailyRow[]
  pages: { path: string; views: number; visitors: number }[]
  referrers: { host: string; visitors: number }[]
  countries: { country: string; visitors: number }[]
  devices: { device: string; visitors: number }[]
}

const RANGES = [7, 30, 90] as const
const REFRESH_MS = 60_000

const card: React.CSSProperties = { background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.25rem" }
const label: React.CSSProperties = { fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.5rem" }
const heading: React.CSSProperties = { ...label, fontWeight: 700, marginBottom: "0.75rem" }
const tooltipStyle = { background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", fontSize: "0.75rem" }

const countryName = (code: string): string => {
  if (code === "??") return "Unknown"
  try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code } catch { return code }
}
const shortDay = (iso: string): string =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })

function Stat({ title, value, note, color }: { title: string; value: number; note?: string; color: string }) {
  return (
    <div style={card}>
      <p style={label}>{title}</p>
      <p style={{ fontSize: "2rem", fontWeight: 800, color, lineHeight: 1 }}>{value.toLocaleString()}</p>
      {note && <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.3rem" }}>{note}</p>}
    </div>
  )
}

function RankList({ title, rows, max }: { title: string; rows: { name: string; value: number; sub?: string }[]; max: number }) {
  return (
    <div style={card}>
      <h2 style={heading}>{title}</h2>
      {rows.length === 0 && <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>No data yet.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {rows.map(r => (
          <div key={r.name}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", fontSize: "0.8rem", marginBottom: "0.25rem" }}>
              <span style={{ color: "var(--gm-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.name}>{r.name}</span>
              <span style={{ color: "var(--gm-text-2)", fontWeight: 600, flexShrink: 0 }}>{r.value.toLocaleString()}{r.sub ? <span style={{ color: "var(--gm-text-3)", fontWeight: 400 }}> {r.sub}</span> : null}</span>
            </div>
            <div style={{ height: "4px", background: "var(--gm-border)", borderRadius: "99px", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${max > 0 ? Math.round((r.value / max) * 100) : 0}%`, background: "var(--gm-blue)", borderRadius: "99px" }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function VisitorAnalytics() {
  const [days, setDays] = useState<(typeof RANGES)[number]>(30)
  const [data, setData] = useState<VisitorData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (range: number) => {
    try {
      const res = await fetch(`/api/admin/analytics/visitors?days=${range}`, { cache: "no-store" })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.error ?? "Could not load visitor analytics.")
      setData(json as VisitorData)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load visitor analytics.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    load(days)
    const timer = setInterval(() => load(days), REFRESH_MS)
    return () => clearInterval(timer)
  }, [days, load])

  if (loading && !data) return <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading visitors…</p>
  if (error && !data) {
    return <div style={{ ...card, borderColor: "#f59e0b", color: "var(--gm-text-2)", fontSize: "0.85rem" }}>{error}</div>
  }
  if (!data) return null

  const t = data.totals
  const chartData = data.daily.map(d => ({ ...d, label: shortDay(d.day) }))
  const avgDaily = data.daily.length ? Math.round(data.daily.reduce((s, d) => s + d.visitors, 0) / data.daily.length) : 0
  const pageMax = data.pages[0]?.views ?? 0
  const refMax = data.referrers[0]?.visitors ?? 0
  const countryMax = data.countries[0]?.visitors ?? 0
  const deviceMax = data.devices[0]?.visitors ?? 0

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1rem" }}>
        <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>
          Unique visitors per day ({data.timezone} time). Refreshes every minute.
          {t.tracking_since && <> Counting since {new Date(t.tracking_since).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}.</>}
        </p>
        <div style={{ display: "flex", gap: "0.25rem" }}>
          {RANGES.map(r => (
            <button key={r} onClick={() => setDays(r)} style={{
              padding: "0.35rem 0.75rem", fontSize: "0.75rem", borderRadius: "0.5rem", cursor: "pointer",
              border: "1px solid var(--gm-border)", fontWeight: days === r ? 700 : 400,
              background: days === r ? "var(--gm-blue)" : "transparent", color: days === r ? "#fff" : "var(--gm-text-2)",
            }}>{r} days</button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Stat title="Online now" value={t.live} note="last 30 minutes" color="#22c55e" />
        <Stat title="Today" value={t.today} note={`yesterday ${t.yesterday.toLocaleString()}`} color="var(--gm-blue)" />
        <Stat title="Last 7 days" value={t.last7} note="unique visitors" color="var(--gm-text)" />
        <Stat title={`${data.days}-day visitors`} value={t.visitors} note={`${t.new_visitors.toLocaleString()} new · avg ${avgDaily.toLocaleString()}/day`} color="#a855f7" />
        <Stat title="Page views" value={t.views} note={t.visitors ? `${(t.views / t.visitors).toFixed(1)} per visitor` : undefined} color="#06b6d4" />
        <Stat title="New accounts" value={t.signups} note={`in ${data.days} days`} color="#f59e0b" />
      </div>

      <div style={{ ...card, marginBottom: "1.5rem" }}>
        <h2 style={heading}>Visitors per day</h2>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "var(--gm-text-3)", fontSize: 11 }} minTickGap={16} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--gm-text-3)", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              <Area type="monotone" dataKey="views" name="Page views" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.12} />
              <Area type="monotone" dataKey="visitors" name="Visitors" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ ...card, marginBottom: "1.5rem" }}>
        <h2 style={heading}>New visitors, signed-in visitors and new accounts</h2>
        <div style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "var(--gm-text-3)", fontSize: 11 }} minTickGap={16} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--gm-text-3)", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              <RBar dataKey="new_visitors" name="New visitors" fill="#a855f7" radius={[3, 3, 0, 0]} />
              <RBar dataKey="signed_in" name="Signed-in visitors" fill="#22c55e" radius={[3, 3, 0, 0]} />
              <RBar dataKey="signups" name="New accounts" fill="#f59e0b" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
        <RankList title="Top pages" max={pageMax}
          rows={data.pages.map(p => ({ name: p.path, value: p.views, sub: `· ${p.visitors.toLocaleString()} visitors` }))} />
        <RankList title="Where visitors come from" max={refMax}
          rows={data.referrers.map(r => ({ name: r.host, value: r.visitors }))} />
        <RankList title="Countries" max={countryMax}
          rows={data.countries.map(c => ({ name: countryName(c.country), value: c.visitors }))} />
        <RankList title="Devices" max={deviceMax}
          rows={data.devices.map(d => ({ name: d.device.charAt(0).toUpperCase() + d.device.slice(1), value: d.visitors }))} />
      </div>
    </div>
  )
}
