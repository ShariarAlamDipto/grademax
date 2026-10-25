"use client"
import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react"
import { toCsv } from "@/lib/analyticsQuery"

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

/** Percentage change from the previous period; null when there is nothing to compare. */
export function change(current: number | null | undefined, previous: number | null | undefined): number | null {
  if (current == null || previous == null || previous === 0) return null
  return Math.round(((current - previous) / previous) * 1000) / 10
}

/**
 * `delta` is the % change from the previous period. `lowerIsBetter` flips the
 * colour for metrics like bounce rate.
 */
export function Stat({ title, value, note, color, delta, lowerIsBetter }: {
  title: string; value: string; note?: string; color: string; delta?: number | null; lowerIsBetter?: boolean
}) {
  const good = delta != null && (lowerIsBetter ? delta < 0 : delta > 0)
  return (
    <div style={card}>
      <p style={label}>{title}</p>
      <p style={{ fontSize: "1.9rem", fontWeight: 800, color, lineHeight: 1 }}>{value}</p>
      {delta != null && (
        <p style={{ fontSize: "0.7rem", fontWeight: 700, marginTop: "0.35rem", color: delta === 0 ? "var(--gm-text-3)" : good ? COLORS.green : COLORS.pink }}>
          {delta > 0 ? "▲" : delta < 0 ? "▼" : "•"} {Math.abs(delta)}% vs previous period
        </p>
      )}
      {note && <p style={{ ...muted, fontSize: "0.7rem", marginTop: "0.3rem" }}>{note}</p>}
    </div>
  )
}

/** Saves rows as a CSV file named `<name>-<date>.csv`. */
export function downloadCsv(name: string, headers: string[], rows: (string | number | null | undefined)[][]): void {
  const blob = new Blob([`﻿${toCsv(headers, rows)}`], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `${name}-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export const smallButton: CSSProperties = {
  padding: "0.3rem 0.7rem", fontSize: "0.72rem", borderRadius: "0.45rem", cursor: "pointer",
  border: "1px solid var(--gm-border)", background: "transparent", color: "var(--gm-text-2)",
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

export interface Column<T> {
  key: string
  title: string
  render: (row: T) => ReactNode
  align?: "left" | "right"
  sort?: (row: T) => number | string
  /** Value written to CSV; defaults to the sort value. */
  csv?: (row: T) => string | number | null
}

const PAGE_SIZE = 25

/**
 * A sortable table that scrolls sideways on small screens instead of the page.
 * `searchText` adds a search box; `exportName` adds a CSV button (all matching
 * rows, not just the visible page). Long tables show 25 rows at a time.
 */
export function DataTable<T>({ rows, columns, initialSort, searchText, exportName }: {
  rows: T[]; columns: Column<T>[]; initialSort?: string; searchText?: (row: T) => string; exportName?: string
}) {
  const [sortKey, setSortKey] = useState(initialSort ?? "")
  const [desc, setDesc] = useState(true)
  const [search, setSearch] = useState("")
  const [shown, setShown] = useState(PAGE_SIZE)
  if (rows.length === 0) return <Empty />

  const needle = search.trim().toLowerCase()
  const filtered = needle && searchText ? rows.filter(r => searchText(r).toLowerCase().includes(needle)) : rows
  const column = columns.find(c => c.key === sortKey && c.sort)
  const sorted = column?.sort
    ? [...filtered].sort((a, b) => {
        const x = column.sort!(a), y = column.sort!(b)
        const cmp = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))
        return desc ? -cmp : cmp
      })
    : filtered
  const visible = sorted.slice(0, shown)
  const exportRows = () => downloadCsv(exportName!, columns.map(c => c.title),
    sorted.map(r => columns.map(c => (c.csv ? c.csv(r) : c.sort ? c.sort(r) : null))))

  const cell: CSSProperties = { padding: "0.5rem 0.6rem", borderBottom: "1px solid var(--gm-border)", whiteSpace: "nowrap" }
  return (
    <div>
      {(searchText || exportName) && (
        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "space-between", flexWrap: "wrap", marginBottom: "0.6rem" }}>
          {searchText ? (
            <input
              type="search" value={search} placeholder="Search…" aria-label="Search table"
              onChange={e => { setSearch(e.target.value); setShown(PAGE_SIZE) }}
              style={{ flex: "1 1 180px", maxWidth: "280px", padding: "0.4rem 0.6rem", fontSize: "0.8rem", borderRadius: "0.45rem",
                border: "1px solid var(--gm-border)", background: "var(--gm-bg)", color: "var(--gm-text)" }}
            />
          ) : <span />}
          {exportName && <button onClick={exportRows} style={smallButton}>Download CSV</button>}
        </div>
      )}
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
          {visible.map((row, i) => (
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
      {filtered.length === 0 && <Empty>No rows match “{search}”.</Empty>}
      {sorted.length > shown && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: "0.6rem" }}>
          <button onClick={() => setShown(shown + PAGE_SIZE)} style={smallButton}>
            Show more ({num(sorted.length - shown)} left)
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * Loads one dashboard section and refreshes it on an interval. `query` is the
 * shell's range and country as a URL query string (see analyticsQuery.ts).
 */
export function useSection<T>(section: string, query: string, refreshMs: number) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/admin/analytics/visitors?section=${section}&${query}`, { cache: "no-store" })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.error ?? "Could not load visitor analytics.")
      setData(json as T)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load visitor analytics.")
    } finally {
      setLoading(false)
    }
  }, [section, query])

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

/** What period a section covers, and whether its last day is still running. */
export function PeriodNote({ firstDay, lastDay, partial, extra }: { firstDay?: string; lastDay?: string; partial?: boolean; extra?: ReactNode }) {
  if (!firstDay || !lastDay) return null
  const fmt = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
  return (
    <p style={{ ...muted, marginBottom: "1rem" }}>
      {firstDay === lastDay ? fmt(firstDay) : `${fmt(firstDay)} – ${fmt(lastDay)}`}
      {partial ? " · today is still in progress" : ""}
      {extra ? <> · {extra}</> : null}
    </p>
  )
}

/** Props every ranged panel receives from the dashboard shell. */
export interface PanelProps {
  query: string
  onPickCountry?: (country: string) => void
}
