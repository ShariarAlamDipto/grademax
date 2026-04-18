"use client"
import { useEffect, useState, useCallback } from "react"

interface AuditEntry {
  id: string
  created_at: string
  admin_email: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  details: Record<string, unknown> | null
}

const ACTION_COLORS: Record<string, string> = {
  upload_paper: "var(--gm-blue)",
  delete_paper: "#ef4444",
  delete_subject: "#ef4444",
  update_role: "#f59e0b",
  deactivate_user: "#ef4444",
}

const PAGE_SIZE = 50

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filterAction, setFilterAction] = useState("")
  const [filterType, setFilterType] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams({
      offset: String(offset),
      limit: String(PAGE_SIZE),
    })
    if (filterAction) params.set("action", filterAction)
    if (filterType) params.set("entity_type", filterType)
    const res = await fetch(`/api/admin/audit-log?${params}`)
    const data = await res.json()
    setEntries(data.entries || [])
    setTotal(data.total || 0)
    if (data.note) setNote(data.note)
    setLoading(false)
  }, [offset, filterAction, filterType])

  useEffect(() => { load() }, [load])

  const inputStyle: React.CSSProperties = {
    background: "var(--gm-bg)", border: "1px solid var(--gm-border)",
    borderRadius: "0.5rem", padding: "0.4rem 0.625rem",
    color: "var(--gm-text)", fontSize: "0.78rem", outline: "none",
  }

  const pageCount = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div style={{ padding: "2rem", maxWidth: "1000px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Audit Log</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Record of all admin write actions</p>
      </div>

      {note && (
        <div style={{ marginBottom: "1.5rem", padding: "0.75rem 1rem", background: "#f59e0b10", border: "1px solid #f59e0b30", borderRadius: "0.75rem", fontSize: "0.8rem", color: "#f59e0b" }}>
          ⚠ {note}. Run this SQL in your Supabase dashboard to enable audit logging:
          <pre style={{ marginTop: "0.5rem", fontFamily: "monospace", fontSize: "0.7rem", color: "var(--gm-text-2)", whiteSpace: "pre-wrap" }}>{`CREATE TABLE IF NOT EXISTS admin_audit_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at  timestamptz DEFAULT now(),
  admin_email text,
  action      text NOT NULL,
  entity_type text,
  entity_id   text,
  details     jsonb
);
CREATE INDEX IF NOT EXISTS admin_audit_log_created_at
  ON admin_audit_log (created_at DESC);`}</pre>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <select value={filterAction} onChange={e => { setFilterAction(e.target.value); setOffset(0) }} style={inputStyle}>
          <option value="">All actions</option>
          <option value="upload_paper">upload_paper</option>
          <option value="delete_paper">delete_paper</option>
          <option value="delete_subject">delete_subject</option>
          <option value="update_role">update_role</option>
          <option value="deactivate_user">deactivate_user</option>
        </select>
        <select value={filterType} onChange={e => { setFilterType(e.target.value); setOffset(0) }} style={inputStyle}>
          <option value="">All types</option>
          <option value="paper">paper</option>
          <option value="subject">subject</option>
          <option value="user">user</option>
        </select>
        <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginLeft: "auto" }}>
          {total} total entries
        </span>
        <button onClick={() => load()} style={{ padding: "0.35rem 0.75rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.75rem", cursor: "pointer" }}>
          Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</div>
      ) : entries.length === 0 ? (
        <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem", padding: "2rem", textAlign: "center", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem" }}>
          No audit entries yet.
        </div>
      ) : (
        <>
          <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "160px 1fr 100px 120px auto", padding: "0.5rem 1rem", borderBottom: "1px solid var(--gm-border)", fontSize: "0.7rem", color: "var(--gm-text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              <span>Time</span><span>Action</span><span>Type</span><span>Admin</span><span></span>
            </div>
            {entries.map((e, i) => (
              <div key={e.id}>
                <div
                  onClick={() => setExpandedId(expandedId === e.id ? null : e.id)}
                  style={{
                    display: "grid", gridTemplateColumns: "160px 1fr 100px 120px auto",
                    padding: "0.625rem 1rem", alignItems: "center",
                    borderBottom: i < entries.length - 1 ? "1px solid var(--gm-border)" : "none",
                    cursor: e.details ? "pointer" : "default",
                  }}
                >
                  <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", fontFamily: "monospace" }}>
                    {new Date(e.created_at).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span style={{ fontSize: "0.78rem", fontWeight: 600, color: ACTION_COLORS[e.action] || "var(--gm-text)" }}>
                    {e.action}
                    {e.entity_id && <span style={{ marginLeft: "0.4rem", fontSize: "0.68rem", color: "var(--gm-text-3)", fontWeight: 400, fontFamily: "monospace" }}>{e.entity_id.slice(0, 8)}…</span>}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)" }}>{e.entity_type || "—"}</span>
                  <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={e.admin_email || undefined}>
                    {e.admin_email?.split("@")[0] || "—"}
                  </span>
                  {e.details && (
                    <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>{expandedId === e.id ? "▲" : "▼"}</span>
                  )}
                </div>
                {expandedId === e.id && e.details && (
                  <div style={{ padding: "0.625rem 1rem", background: "var(--gm-bg)", borderBottom: i < entries.length - 1 ? "1px solid var(--gm-border)" : "none" }}>
                    <pre style={{ fontFamily: "monospace", fontSize: "0.72rem", color: "var(--gm-text-2)", margin: 0 }}>
                      {JSON.stringify(e.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {pageCount > 1 && (
            <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.75rem" }}>
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                style={{ padding: "0.4rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: offset === 0 ? "not-allowed" : "pointer", opacity: offset === 0 ? 0.4 : 1 }}
              >
                ← Prev
              </button>
              <span style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
                Page {currentPage} of {pageCount}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                style={{ padding: "0.4rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: offset + PAGE_SIZE >= total ? "not-allowed" : "pointer", opacity: offset + PAGE_SIZE >= total ? 0.4 : 1 }}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
