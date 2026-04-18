"use client"
import { useEffect, useState } from "react"

interface Subject {
  id: string; name: string; code: string | null; board: string | null; level: string; paperCount: number; is_active?: boolean
}

const inputStyle: React.CSSProperties = {
  background: "var(--gm-bg)", border: "1px solid var(--gm-border)",
  borderRadius: "0.5rem", padding: "0.5rem 0.75rem",
  color: "var(--gm-text)", fontSize: "0.8rem", width: "100%", outline: "none",
}

export default function SubjectsAdminPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<Subject | null>(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ name: "", code: "", board: "", level: "IGCSE" })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null)
  const [search, setSearch] = useState("")

  const load = () => {
    setLoading(true)
    fetch("/api/admin/subjects").then(r => r.json()).then(d => {
      setSubjects(d.subjects || [])
      setLoading(false)
    })
  }

  useEffect(() => { load() }, [])

  const startEdit = (s: Subject) => {
    setEditing(s)
    setAdding(false)
    setForm({ name: s.name, code: s.code || "", board: s.board || "", level: s.level })
    setMsg(null)
  }

  const startAdd = () => {
    setAdding(true)
    setEditing(null)
    setForm({ name: "", code: "", board: "Pearson Edexcel", level: "IGCSE" })
    setMsg(null)
  }

  const cancel = () => { setEditing(null); setAdding(false); setMsg(null) }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMsg(null)

    const body = editing
      ? { id: editing.id, ...form }
      : form

    const res = await fetch("/api/admin/subjects", {
      method: editing ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (res.ok) {
      setMsg({ type: "ok", text: editing ? "Subject updated" : "Subject created" })
      cancel()
      load()
    } else {
      setMsg({ type: "err", text: data.error || "Failed" })
    }
    setSaving(false)
  }

  const handleDelete = async (id: string, name: string, paperCount: number) => {
    const impact = paperCount > 0
      ? `⚠ This will also delete ${paperCount} paper record(s).\n\n`
      : ""
    if (!confirm(`${impact}Delete "${name}"? This cannot be undone.`)) return
    const res = await fetch(`/api/admin/subjects?id=${id}`, { method: "DELETE" })
    if (res.ok) { setMsg({ type: "ok", text: `Deleted "${name}"` }); load() }
    else { const d = await res.json(); setMsg({ type: "err", text: d.error || "Delete failed" }) }
  }

  const filtered = subjects.filter(s =>
    !search || s.name.toLowerCase().includes(search.toLowerCase()) || (s.code || "").toLowerCase().includes(search.toLowerCase())
  )
  const igcse = filtered.filter(s => s.level === "IGCSE")
  const ial = filtered.filter(s => s.level === "IAL")
  const other = filtered.filter(s => s.level !== "IGCSE" && s.level !== "IAL")

  const handleToggleActive = async (s: Subject) => {
    const newActive = !(s.is_active ?? true)
    const res = await fetch("/api/admin/subjects", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: s.id, is_active: newActive }),
    })
    if (res.ok) {
      setSubjects(prev => prev.map(x => x.id === s.id ? { ...x, is_active: newActive } : x))
    } else {
      const d = await res.json()
      setMsg({ type: "err", text: d.error || "Toggle failed" })
    }
  }

  const SubjectRow = ({ s }: { s: Subject }) => {
    const active = s.is_active ?? true
    return (
      <div style={{
        display: "grid", gridTemplateColumns: "1fr auto auto auto auto", gap: "0.75rem",
        alignItems: "center", padding: "0.625rem 0.875rem",
        borderBottom: "1px solid var(--gm-border)",
        opacity: active ? 1 : 0.55,
      }}>
        <div>
          <span style={{ fontWeight: 500, fontSize: "0.875rem", color: "var(--gm-text)" }}>{s.name}</span>
          {s.code && <span style={{ marginLeft: "0.5rem", fontSize: "0.7rem", color: "var(--gm-text-3)", background: "var(--gm-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.25rem", padding: "0 0.3rem" }}>{s.code}</span>}
          {!active && <span style={{ marginLeft: "0.5rem", fontSize: "0.65rem", color: "#f59e0b", background: "#f59e0b15", border: "1px solid #f59e0b30", borderRadius: "0.25rem", padding: "0 0.3rem" }}>inactive</span>}
        </div>
        <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>{s.paperCount} papers</span>
        <button
          onClick={() => handleToggleActive(s)}
          title={active ? "Deactivate subject (hides from students)" : "Activate subject"}
          style={{ fontSize: "0.7rem", color: active ? "#f59e0b" : "#22c55e", background: "none", border: "none", cursor: "pointer", padding: "0.25rem 0.5rem" }}
        >
          {active ? "Deactivate" : "Activate"}
        </button>
        <button onClick={() => startEdit(s)} style={{ fontSize: "0.75rem", color: "var(--gm-blue)", background: "none", border: "none", cursor: "pointer", padding: "0.25rem 0.5rem" }}>Edit</button>
        <button onClick={() => handleDelete(s.id, s.name, s.paperCount)} style={{ fontSize: "0.75rem", color: "#ef4444", background: "none", border: "none", cursor: "pointer", padding: "0.25rem 0.5rem" }}>Delete</button>
      </div>
    )
  }

  const Section = ({ label, items }: { label: string; items: Subject[] }) => items.length === 0 ? null : (
    <div style={{ marginBottom: "1.5rem" }}>
      <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)", padding: "0.5rem 0.875rem", background: "var(--gm-bg)", borderBottom: "1px solid var(--gm-border)" }}>
        {label} ({items.length})
      </div>
      {items.map(s => <SubjectRow key={s.id} s={s} />)}
    </div>
  )

  return (
    <div style={{ padding: "2rem", maxWidth: "900px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Subjects</h1>
          <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>{subjects.length} subjects across all levels</p>
        </div>
        <button onClick={startAdd} style={{
          padding: "0.5rem 1.25rem", background: "var(--gm-blue)", color: "#fff",
          borderRadius: "0.5rem", border: "none", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer",
        }}>
          + Add Subject
        </button>
      </div>

      {msg && (
        <div style={{ marginBottom: "1rem", padding: "0.625rem 0.875rem", borderRadius: "0.5rem", fontSize: "0.8rem", background: msg.type === "ok" ? "#22c55e10" : "#ef444410", border: `1px solid ${msg.type === "ok" ? "#22c55e30" : "#ef444430"}`, color: msg.type === "ok" ? "#22c55e" : "#ef4444" }}>
          {msg.text}
        </div>
      )}

      {/* Add/Edit form */}
      {(adding || editing) && (
        <form onSubmit={handleSave} style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.25rem", marginBottom: "1.5rem" }}>
          <p style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--gm-text)", marginBottom: "0.75rem" }}>
            {editing ? `Edit: ${editing.name}` : "New Subject"}
          </p>
          {editing && editing.paperCount > 0 && (
            <div style={{ marginBottom: "0.75rem", padding: "0.5rem 0.75rem", background: "#f59e0b10", border: "1px solid #f59e0b30", borderRadius: "0.5rem", fontSize: "0.75rem", color: "#f59e0b" }}>
              ⚠ This subject has {editing.paperCount} paper(s). Renaming it will break all R2 file paths — the server will reject a name change.
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Name *</label>
              <input style={inputStyle} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required placeholder="Mathematics B" />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Code</label>
              <input style={inputStyle} value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} placeholder="4MB1" />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Board</label>
              <input style={inputStyle} value={form.board} onChange={e => setForm(f => ({ ...f, board: e.target.value }))} placeholder="Pearson Edexcel" />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Level *</label>
              <select style={inputStyle} value={form.level} onChange={e => setForm(f => ({ ...f, level: e.target.value }))}>
                <option value="IGCSE">IGCSE</option>
                <option value="IAL">IAL</option>
                <option value="GCSE">GCSE</option>
                <option value="A Level">A Level</option>
              </select>
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button type="submit" disabled={saving} style={{ padding: "0.5rem 1.25rem", background: "var(--gm-blue)", color: "#fff", borderRadius: "0.5rem", border: "none", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer", opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button type="button" onClick={cancel} style={{ padding: "0.5rem 1rem", background: "var(--gm-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-3)", fontSize: "0.875rem", cursor: "pointer" }}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Search */}
      <div style={{ marginBottom: "1.25rem" }}>
        <input
          style={{ ...inputStyle, width: "auto", minWidth: "280px" }}
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search subjects…"
        />
      </div>

      {loading ? (
        <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</div>
      ) : (
        <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden" }}>
          <Section label="IGCSE" items={igcse} />
          <Section label="IAL" items={ial} />
          <Section label="Other" items={other} />
          {filtered.length === 0 && (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--gm-text-3)", fontSize: "0.875rem" }}>No subjects found</div>
          )}
        </div>
      )}
    </div>
  )
}
