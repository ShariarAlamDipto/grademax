"use client"
import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react"

/** Shared pieces for the Visitors dashboard panels. */

export const card: CSSProperties = { background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.25rem" }
export const label: CSSProperties = { fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.5rem" }
export const heading: CSSProperties = { ...label, fontWeight: 700, marginBottom: "0.75rem" }
export const muted: CSSProperties = { fontSize: "0.75rem", color: "var(--gm-text-3)" }
export const tooltipStyle = { background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", fontSize: "0.75rem" }
export const axisTick = { fill: "var(--gm-text-3)", fontSize: 11 }
export const statGrid: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }
export const panelGrid: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }

export const COLORS = {
  blue: "#3b82f6", cyan: "#06b6d4", purple: "#a855f7", green: "#22c55e", amber: "#f59e0b", pink: "#ec4899", slate: "#94a3b8",
}

export const CHANNEL_LABELS: Record<string, string> = {
  search: "Search (Google, Bing…)", direct: "Direct", social: "Social", ai: "AI assistants",
  referral: "Other websites", email: "Email", paid: "Paid ads", campaigns: "Campaigns",
}
export const CHANNEL_COLORS: Record<string, string> = {
  search: COLORS.blue, direct: COLORS.slate, social: COLORS.pink, ai: COLORS.purple,
  referral: COLORS.cyan, email: COLORS.amber, paid: COLORS.green, campaigns: COLORS.amber,
}

export function formatSeconds(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—"
  const s = Math.round(value)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${String(s % 60).padStart(2, "0")}s`
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`
}

export const pct = (value: number | null | undefined): string => (value == null ? "—" : `${value}%`)
export const num = (value: number | null | undefined): string => (value == null ? "—" : value.toLocaleString())

export const shortDay = (iso: string): string =>
  new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })

export function countryName(code: string): string {
  if (!code || code === "??") return "Unknown"
  try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code } catch { return code }
}

export function Stat({ title, value, note, color }: { title: string; value: string; note?: string; color: string }) {
  return (
    <div style={card}>
      <p style={label}>{title}</p>
      <p style={{ fontSize: "1.9rem", fontWeight: 800, color, lineHeight: 1 }}>{value}</p>
      {note && <p style={{ ...muted, fontSize: "0.7rem", marginTop: "0.3rem" }}>{note}</p>}
    </div>
  )
}

export function Panel({ title, note, children, style }: { title: string; note?: string; children: ReactNode; style?: CSSProperties }) {
  return (
    <div style={{ ...card, ...style }}>
      <h2 style={heading}>{title}</h2>
      {note && <p style={{ ...muted, marginTop: "-0.4rem", marginBottom: "0.75rem" }}>{note}</p>}
      {children}
    </div>
  )
}

export function Empty({ children = "No data yet. It fills in as visitors arrive." }: { children?: ReactNode }) {
  return <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>{children}</p>
}

export interface RankRow { name: string; value: number; sub?: string; color?: string }

export function RankList({ rows, max }: { rows: RankRow[]; max?: number }) {
  if (rows.length === 0) return <Empty />
  const top = max ?? Math.max(...rows.map(r => r.value), 0)
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
      {rows.map(r => (
        <div key={r.name}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", fontSize: "0.8rem", marginBottom: "0.25rem" }}>
            <span style={{ color: "var(--gm-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.name}>{r.name}</span>
            <span style={{ color: "var(--gm-text-2)", fontWeight: 600, flexShrink: 0 }}>
              {r.value.toLocaleString()}{r.sub ? <span style={{ color: "var(--gm-text-3)", fontWeight: 400 }}> {r.sub}</span> : null}
            </span>
          </div>
          <div style={{ height: "4px", background: "var(--gm-border)", borderRadius: "99px", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${top > 0 ? Math.round((r.value / top) * 100) : 0}%`, background: r.color ?? "var(--gm-blue)", borderRadius: "99px" }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export interface Column<T> { key: string; title: string; render: (row: T) => ReactNode; align?: "left" | "right"; sort?: (row: T) => number | string }

/** A sortable table that scrolls sideways on small screens instead of the page. */
export function DataTable<T>({ rows, columns, initialSort }: { rows: T[]; columns: Column<T>[]; initialSort?: string }) {
  const [sortKey, setSortKey] = useState(initialSort ?? "")
  const [desc, setDesc] = useState(true)
  if (rows.length === 0) return <Empty />
  const column = columns.find(c => c.key === sortKey && c.sort)
  const sorted = column?.sort
    ? [...rows].sort((a, b) => {
        const x = column.sort!(a), y = column.sort!(b)
        const cmp = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))
        return desc ? -cmp : cmp
      })
    : rows
  const cell: CSSProperties = { padding: "0.5rem 0.6rem", borderBottom: "1px solid var(--gm-border)", whiteSpace: "nowrap" }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
        <thead>
          <tr>
            {columns.map(c => (
              <th key={c.key} style={{ ...cell, textAlign: c.align ?? "left", color: "var(--gm-text-3)", fontWeight: 600, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                {c.sort ? (
                  <button
                    onClick={() => { if (sortKey === c.key) setDesc(!desc); else { setSortKey(c.key); setDesc(true) } }}
                    style={{ background: "none", border: "none", color: "inherit", font: "inherit", cursor: "pointer", padding: 0, textTransform: "inherit", letterSpacing: "inherit" }}
                  >
                    {c.title}{sortKey === c.key ? (desc ? " ↓" : " ↑") : ""}
                  </button>
                ) : c.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={i}>
              {columns.map(c => (
                <td key={c.key} style={{ ...cell, textAlign: c.align ?? "left", color: c.align === "right" ? "var(--gm-text-2)" : "var(--gm-text)", maxWidth: c.align === "right" ? undefined : "320px", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Loads one dashboard section and refreshes it on an interval. */
export function useSection<T>(section: string, days: number, refreshMs: number) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/admin/analytics/visitors?section=${section}&days=${days}`, { cache: "no-store" })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.error ?? "Could not load visitor analytics.")
      setData(json as T)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load visitor analytics.")
    } finally {
      setLoading(false)
    }
  }, [section, days])

  useEffect(() => {
    setLoading(true)
    load()
    const timer = setInterval(load, refreshMs)
    return () => clearInterval(timer)
  }, [load, refreshMs])

  return { data, error, loading }
}

/** Loading and error states shared by every panel. */
export function SectionState({ loading, error, hasData }: { loading: boolean; error: string | null; hasData: boolean }) {
  if (loading && !hasData) return <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</p>
  if (error && !hasData) return <div style={{ ...card, borderColor: COLORS.amber, color: "var(--gm-text-2)", fontSize: "0.85rem" }}>{error}</div>
  return null
}
