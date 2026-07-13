"use client"
import { useEffect, useState, useCallback } from "react"

interface Suggestion {
  id: string
  user_id: string | null
  name: string | null
  email: string | null
  message: string
  status: "new" | "reviewed" | "in_progress" | "done" | "archived"
  admin_notes: string | null
  created_at: string
  updated_at: string
}

const STATUS_OPTIONS: Suggestion["status"][] = ["new", "reviewed", "in_progress", "done", "archived"]

const STATUS_COLORS: Record<Suggestion["status"], { bg: string; fg: string }> = {
  new:         { bg: "rgba(245,158,11,0.18)", fg: "#f59e0b" },
  reviewed:    { bg: "rgba(110,168,254,0.18)", fg: "#6EA8FE" },
  in_progress: { bg: "rgba(168,85,247,0.18)", fg: "#a855f7" },
  done:        { bg: "rgba(34,197,94,0.18)", fg: "#22c55e" },
  archived:    { bg: "rgba(120,120,120,0.20)", fg: "#999" },
}

export default function AdminSuggestionsPage() {
  const [items, setItems] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<"all" | Suggestion["status"]>("all")
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const url = filter === "all" ? "/api/admin/suggestions" : `/api/admin/suggestions?status=${filter}`
      const res = await fetch(url)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? "Failed to load")
      setItems(data.suggestions ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load")
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { load() }, [load])

  async function updateStatus(id: string, status: Suggestion["status"]) {
    const prev = items
    setItems(items.map(i => i.id === id ? { ...i, status } : i))
    const res = await fetch("/api/admin/suggestions", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status }),
    })
    if (!res.ok) setItems(prev)
  }

  async function remove(id: string) {
    if (!confirm("Delete this suggestion permanently?")) return
    const prev = items
    setItems(items.filter(i => i.id !== id))
    const res = await fetch(`/api/admin/suggestions?id=${id}`, { method: "DELETE" })
    if (!res.ok) setItems(prev)
  }

  const counts = STATUS_OPTIONS.reduce<Record<string, number>>((acc, s) => {
    acc[s] = items.filter(i => i.status === s).length
    return acc
  }, {})

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Suggestions</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>
          User-submitted improvements from /improvements
        </p>
      </div>

      {/* Filter pills */}
      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        {(["all", ...STATUS_OPTIONS] as const).map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            style={{
              padding: "0.35rem 0.8rem",
              borderRadius: "99px",
              border: filter === s ? "1px solid var(--gm-amber)" : "1px solid var(--gm-border-2)",
              background: filter === s ? "rgba(245,158,11,0.10)" : "var(--gm-card-bg)",
              color: filter === s ? "var(--gm-amber)" : "var(--gm-text-2)",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {s === "all" ? `All (${items.length})` : `${s.replace("_", " ")} (${counts[s] ?? 0})`}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "rgba(239,68,68,0.10)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444", borderRadius: "0.5rem", marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      {loading && <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</p>}

      {!loading && items.length === 0 && (
        <div style={{
          padding: "3rem 1.5rem",
          textAlign: "center",
          background: "var(--gm-surface)",
          border: "1px dashed var(--gm-border-2)",
          borderRadius: "0.75rem",
          color: "var(--gm-text-3)",
          fontSize: "0.9rem",
        }}>
          No suggestions yet.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {items.map(item => {
          const color = STATUS_COLORS[item.status]
          const submitted = new Date(item.created_at)
          return (
            <article key={item.id} style={{
              background: "var(--gm-surface)",
              border: "1px solid var(--gm-border)",
              borderRadius: "0.75rem",
              padding: "1.1rem 1.25rem",
            }}>
              <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.65rem", flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
                  <span style={{
                    padding: "0.18rem 0.55rem",
                    borderRadius: "99px",
                    background: color.bg,
                    color: color.fg,
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}>
                    {item.status.replace("_", " ")}
                  </span>
                  <span style={{ fontSize: "0.78rem", color: "var(--gm-text-2)" }}>
                    {item.name || "Anonymous"}
                    {item.email && (
                      <>
                        {" · "}
                        <a href={`mailto:${item.email}`} style={{ color: "#6EA8FE", textDecoration: "none" }}>{item.email}</a>
                      </>
                    )}
                  </span>
                </div>
                <time style={{ fontSize: "0.72rem", color: "var(--gm-text-3)" }}>
                  {submitted.toLocaleString()}
                </time>
              </header>

              <p style={{
                color: "var(--gm-text)",
                fontSize: "0.92rem",
                lineHeight: 1.65,
                whiteSpace: "pre-wrap",
                margin: "0 0 0.85rem 0",
              }}>
                {item.message}
              </p>

              <div style={{ display: "flex", gap: "0.4rem", alignItems: "center", flexWrap: "wrap" }}>
                <label style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", fontWeight: 600 }}>Set status:</label>
                <select
                  value={item.status}
                  onChange={e => updateStatus(item.id, e.target.value as Suggestion["status"])}
                  style={{
                    padding: "0.3rem 0.55rem",
                    background: "var(--gm-bg)",
                    color: "var(--gm-text)",
                    border: "1px solid var(--gm-border-2)",
                    borderRadius: "0.4rem",
                    fontSize: "0.78rem",
                  }}
                >
                  {STATUS_OPTIONS.map(s => (
                    <option key={s} value={s}>{s.replace("_", " ")}</option>
                  ))}
                </select>
                <div style={{ flex: 1 }} />
                <button
                  onClick={() => remove(item.id)}
                  style={{
                    padding: "0.3rem 0.7rem",
                    background: "transparent",
                    color: "#ef4444",
                    border: "1px solid rgba(239,68,68,0.35)",
                    borderRadius: "0.4rem",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Delete
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
