"use client"
import { useState, useEffect, useCallback, useMemo } from "react"

interface UserEntry {
  id: string; email: string | null; full_name: string | null; role: string; created_at: string
}

const roleColors: Record<string, string> = {
  admin: "#ef4444",
  teacher: "var(--gm-blue)",
  student: "#22c55e",
}

const SENSITIVE_ROLES = new Set(["admin"])

export default function UsersAdminPage() {
  const [users, setUsers] = useState<UserEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState<"all" | "admin" | "teacher" | "student">("all")
  const [changingRole, setChangingRole] = useState<string | null>(null)
  const [deactivating, setDeactivating] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"list" | "assign">("list")
  const [assignEmail, setAssignEmail] = useState("")
  const [assignRole, setAssignRole] = useState<"student" | "teacher" | "admin">("teacher")
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null)

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    const res = await fetch("/api/admin/users")
    if (res.ok) {
      const data = await res.json()
      setUsers(data.users || [])
    }
    setLoading(false)
  }, [])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  const handleInlineRoleChange = async (u: UserEntry, newRole: string) => {
    if (newRole === u.role) return
    // Confirm before granting or revoking admin
    if (SENSITIVE_ROLES.has(newRole) || SENSITIVE_ROLES.has(u.role)) {
      const action = SENSITIVE_ROLES.has(newRole)
        ? `grant Admin to ${u.email || u.full_name}`
        : `revoke Admin from ${u.email || u.full_name}`
      if (!confirm(`Are you sure you want to ${action}?\n\nAdmin users have full access to the admin panel.`)) return
    }
    setChangingRole(u.id)
    setMsg(null)
    const res = await fetch("/api/admin/users", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: u.email, role: newRole }),
    })
    if (res.ok) {
      setUsers(prev => prev.map(x => x.id === u.id ? { ...x, role: newRole } : x))
      setMsg({ type: "ok", text: `${u.email} role updated to ${newRole}` })
    } else {
      const d = await res.json()
      setMsg({ type: "err", text: d.error || "Role change failed" })
    }
    setChangingRole(null)
  }

  const handleDeactivate = async (u: UserEntry) => {
    if (!confirm(`Deactivate ${u.email || u.full_name}?\n\nThis will ban the account and downgrade their role to student. The action can be reversed from the Supabase dashboard.`)) return
    setDeactivating(u.id)
    setMsg(null)
    const res = await fetch(`/api/admin/users?id=${u.id}`, { method: "DELETE" })
    const data = await res.json()
    if (res.ok) {
      setMsg({ type: "ok", text: `${u.email} deactivated` })
      fetchUsers()
    } else {
      setMsg({ type: "err", text: data.error || "Deactivation failed" })
    }
    setDeactivating(null)
  }

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault()
    setMsg(null)
    const res = await fetch("/api/admin/users", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: assignEmail.trim(), role: assignRole }),
    })
    const data = await res.json()
    if (res.ok) {
      setMsg({ type: "ok", text: `${assignEmail} is now a ${assignRole}` })
      setAssignEmail("")
      fetchUsers()
    } else {
      setMsg({ type: "err", text: data.error || "Failed" })
    }
  }

  const filtered = useMemo(() => users.filter(u => {
    if (roleFilter !== "all" && u.role !== roleFilter) return false
    if (!search) return true
    const q = search.toLowerCase()
    return u.email?.toLowerCase().includes(q) || u.full_name?.toLowerCase().includes(q) || u.role.includes(q)
  }), [users, search, roleFilter])

  const stats = useMemo(() => {
    const admins = users.filter(u => u.role === "admin").length
    const teachers = users.filter(u => u.role === "teacher").length
    return { total: users.length, admins, teachers, students: users.length - admins - teachers }
  }, [users])

  const inputStyle: React.CSSProperties = {
    background: "var(--gm-bg)", border: "1px solid var(--gm-border)",
    borderRadius: "0.5rem", padding: "0.5rem 0.75rem",
    color: "var(--gm-text)", fontSize: "0.8rem", outline: "none",
  }

  const avatar = (u: UserEntry) => (u.full_name || u.email || "?").split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)

  return (
    <div style={{ padding: "2rem", maxWidth: "1000px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Users</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Manage accounts and assign roles</p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", marginBottom: "1.5rem" }}>
        {[
          { label: "Total", value: stats.total, color: "var(--gm-text)", filter: "all" as const },
          { label: "Admins", value: stats.admins, color: "#ef4444", filter: "admin" as const },
          { label: "Teachers", value: stats.teachers, color: "var(--gm-blue)", filter: "teacher" as const },
          { label: "Students", value: stats.students, color: "#22c55e", filter: "student" as const },
        ].map(s => (
          <div
            key={s.label}
            onClick={() => { setRoleFilter(s.filter); setActiveTab("list") }}
            style={{
              background: roleFilter === s.filter ? `${s.color}10` : "var(--gm-surface)",
              border: `1px solid ${roleFilter === s.filter ? s.color + "60" : "var(--gm-border)"}`,
              borderRadius: "0.75rem", padding: "1rem", cursor: "pointer",
            } as React.CSSProperties}
          >
            <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.25rem" }}>{s.label}</p>
            <p style={{ fontSize: "1.5rem", fontWeight: 800, color: s.color }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--gm-border)", marginBottom: "1.5rem" }}>
        {(["list", "assign"] as const).map(tab => (
          <button key={tab} onClick={() => { setActiveTab(tab); setMsg(null) }} style={{
            padding: "0.625rem 1.25rem", fontSize: "0.8rem", fontWeight: activeTab === tab ? 600 : 400,
            color: activeTab === tab ? "var(--gm-text)" : "var(--gm-text-3)",
            borderBottom: activeTab === tab ? "2px solid var(--gm-blue)" : "2px solid transparent",
            background: "transparent", border: "none", cursor: "pointer", textTransform: "capitalize",
          }}>
            {tab === "list" ? "All Users" : "Assign Role"}
          </button>
        ))}
      </div>

      {msg && (
        <div style={{ marginBottom: "1rem", padding: "0.625rem 0.875rem", borderRadius: "0.5rem", fontSize: "0.8rem", background: msg.type === "ok" ? "#22c55e10" : "#ef444410", border: `1px solid ${msg.type === "ok" ? "#22c55e30" : "#ef444430"}`, color: msg.type === "ok" ? "#22c55e" : "#ef4444" }}>
          {msg.text}
        </div>
      )}

      {/* User list */}
      {activeTab === "list" && (
        <div>
          <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap", alignItems: "center" }}>
            <input style={{ ...inputStyle, minWidth: "260px" }} value={search} onChange={e => setSearch(e.target.value)} placeholder="Search users…" />
            {/* Role filter pills */}
            <div style={{ display: "flex", gap: "0.35rem" }}>
              {([
                { key: "all", label: "All" },
                { key: "admin", label: "Admins" },
                { key: "teacher", label: "Teachers" },
                { key: "student", label: "Students" },
              ] as const).map(f => (
                <button
                  key={f.key}
                  onClick={() => setRoleFilter(f.key)}
                  style={{
                    padding: "0.25rem 0.625rem", borderRadius: "999px", fontSize: "0.72rem", cursor: "pointer",
                    background: roleFilter === f.key ? "var(--gm-text)" : "var(--gm-surface)",
                    color: roleFilter === f.key ? "var(--gm-bg)" : "var(--gm-text-3)",
                    border: `1px solid ${roleFilter === f.key ? "var(--gm-text)" : "var(--gm-border)"}`,
                    fontWeight: roleFilter === f.key ? 600 : 400,
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <button onClick={fetchUsers} disabled={loading} style={{ padding: "0.5rem 1rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text)", fontSize: "0.8rem", cursor: "pointer", marginLeft: "auto" }}>
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
          <div style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr auto", padding: "0.5rem 1rem", borderBottom: "1px solid var(--gm-border)", fontSize: "0.7rem", color: "var(--gm-text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              <span>Name</span><span>Email</span><span>Joined</span><span>Role</span><span></span>
            </div>
            {loading ? (
              <div style={{ padding: "2rem", textAlign: "center", color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading…</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: "2rem", textAlign: "center", color: "var(--gm-text-3)", fontSize: "0.875rem" }}>No users found</div>
            ) : filtered.map(u => (
              <div key={u.id} style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr auto", padding: "0.625rem 1rem", borderBottom: "1px solid var(--gm-border)", alignItems: "center", gap: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                  <div style={{ width: "1.75rem", height: "1.75rem", borderRadius: "50%", background: `${roleColors[u.role] || "var(--gm-text-3)"}20`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.65rem", fontWeight: 700, color: roleColors[u.role] || "var(--gm-text-3)", flexShrink: 0 }}>
                    {avatar(u)}
                  </div>
                  <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--gm-text)" }}>{u.full_name || "—"}</span>
                </div>
                <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.email}</span>
                <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>{new Date(u.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "2-digit" })}</span>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <select
                    value={u.role}
                    onChange={e => handleInlineRoleChange(u, e.target.value)}
                    disabled={changingRole === u.id}
                    style={{ ...inputStyle, padding: "0.25rem 0.5rem", fontSize: "0.75rem", color: roleColors[u.role] || "var(--gm-text)" }}
                  >
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                    <option value="admin">Admin</option>
                  </select>
                  {changingRole === u.id && <div style={{ width: "0.875rem", height: "0.875rem", border: "2px solid var(--gm-border)", borderTopColor: "var(--gm-blue)", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />}
                </div>
                <button
                  onClick={() => handleDeactivate(u)}
                  disabled={deactivating === u.id || u.role === "admin"}
                  title={u.role === "admin" ? "Cannot deactivate admins" : "Deactivate this user"}
                  style={{ padding: "0.2rem 0.5rem", background: "#ef444410", border: "1px solid #ef444425", borderRadius: "0.375rem", color: "#ef4444", fontSize: "0.7rem", cursor: u.role === "admin" ? "not-allowed" : "pointer", opacity: u.role === "admin" ? 0.3 : 1, whiteSpace: "nowrap" }}
                >
                  {deactivating === u.id ? "…" : "Deactivate"}
                </button>
              </div>
            ))}
            <div style={{ padding: "0.625rem 1rem", fontSize: "0.75rem", color: "var(--gm-text-3)", textAlign: "right" }}>
              {filtered.length} of {users.length} users
            </div>
          </div>
        </div>
      )}

      {/* Assign role tab */}
      {activeTab === "assign" && (
        <form onSubmit={handleAssign} style={{ maxWidth: "420px", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", padding: "1.5rem" }}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>Email Address</label>
            <input type="email" required style={{ ...inputStyle, width: "100%" }} value={assignEmail} onChange={e => setAssignEmail(e.target.value)} placeholder="user@example.com" />
          </div>
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.5rem" }}>Role</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {(["student", "teacher", "admin"] as const).map(r => (
                <button key={r} type="button" onClick={() => setAssignRole(r)} style={{
                  flex: 1, padding: "0.625rem", borderRadius: "0.5rem", fontSize: "0.8rem", fontWeight: 500, cursor: "pointer",
                  background: assignRole === r ? `${roleColors[r]}20` : "var(--gm-bg)",
                  border: `1px solid ${assignRole === r ? roleColors[r] + "60" : "var(--gm-border)"}`,
                  color: assignRole === r ? roleColors[r] : "var(--gm-text-3)",
                }}>
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <button type="submit" style={{ width: "100%", padding: "0.625rem", background: "var(--gm-blue)", color: "#fff", borderRadius: "0.5rem", border: "none", fontSize: "0.875rem", fontWeight: 600, cursor: "pointer" }}>
            Assign Role
          </button>
        </form>
      )}
    </div>
  )
}
