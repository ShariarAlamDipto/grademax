"use client"
import { useAuth } from "@/context/AuthContext"
import { useState, useEffect, useCallback } from "react"
import Link from "next/link"

const SUPER_ADMIN_EMAIL = "shariardipto111@gmail.com"
function isSuperAdminClient(email: string | undefined | null): boolean {
  if (!email) return false
  return email.toLowerCase() === SUPER_ADMIN_EMAIL.toLowerCase()
}

interface UserEntry {
  id: string
  email: string | null
  full_name: string | null
  role: string
  created_at: string
}

export default function AdminPage() {
  const { user, profile, loading: authLoading, refreshProfile } = useAuth()
  const [users, setUsers] = useState<UserEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState("")
  const [roleToAssign, setRoleToAssign] = useState<"student" | "teacher" | "admin">("teacher")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [changingRole, setChangingRole] = useState<string | null>(null)
  const [bootstrapping, setBootstrapping] = useState(false)
  const [bootstrapError, setBootstrapError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"users" | "assign">("users")

  const isAdmin = profile?.role === "admin" || isSuperAdminClient(user?.email)

  // Auto-bootstrap admin on load
  useEffect(() => {
    if (user && !authLoading && (!profile || profile.role !== "admin") && isSuperAdminClient(user.email)) {
      setBootstrapping(true)
      setBootstrapError(null)
      fetch("/api/admin/bootstrap", { method: "POST" })
        .then(async (res) => {
          if (res.ok) {
            await refreshProfile()
          } else {
            const data = await res.json().catch(() => null)
            console.error("Bootstrap failed:", res.status, data)
            setBootstrapError(data?.error || `Bootstrap failed (${res.status})`)
          }
        })
        .catch((err) => {
          console.error("Bootstrap error:", err)
          setBootstrapError(err.message || "Network error")
        })
        .finally(() => setBootstrapping(false))
    }
  }, [user, authLoading, profile, refreshProfile])

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/admin/users")
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users || [])
      } else {
        const data = await res.json().catch(() => null)
        console.error("Failed to fetch users:", res.status, data)
        setError(data?.error || `Failed to load users (${res.status})`)
      }
    } catch (err) {
      console.error("Fetch users error:", err)
      setError("Network error loading users")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (user && isAdmin) {
      fetchUsers()
    }
  }, [user, isAdmin, fetchUsers])

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess("")

    if (!email.trim()) {
      setError("Please enter an email")
      return
    }

    const res = await fetch("/api/admin/users", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), role: roleToAssign }),
    })

    const data = await res.json()
    if (!res.ok) {
      setError(data.error || "Failed to update role")
    } else {
      setSuccess(`${email} is now a ${roleToAssign}`)
      setEmail("")
      fetchUsers()
    }
  }

  const handleInlineRoleChange = async (userEntry: UserEntry, newRole: string) => {
    if (newRole === userEntry.role) return
    setChangingRole(userEntry.id)

    const res = await fetch("/api/admin/users", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: userEntry.email, role: newRole }),
    })

    if (res.ok) {
      setUsers((prev) =>
        prev.map((u) => (u.id === userEntry.id ? { ...u, role: newRole } : u))
      )
    }
    setChangingRole(null)
  }

  const filteredUsers = users.filter((u) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      u.email?.toLowerCase().includes(q) ||
      u.full_name?.toLowerCase().includes(q) ||
      u.role.toLowerCase().includes(q)
    )
  })

  const stats = {
    total: users.length,
    admins: users.filter((u) => u.role === "admin").length,
    teachers: users.filter((u) => u.role === "teacher").length,
    students: users.filter((u) => u.role === "student").length,
  }

  const roleColor = (role: string) => {
    switch (role) {
      case "admin":
        return "text-red-400 bg-red-400/10 border-red-400/20"
      case "teacher":
        return "text-blue-400 bg-blue-400/10 border-blue-400/20"
      default:
        return "text-green-400 bg-green-400/10 border-green-400/20"
    }
  }

  const roleIcon = (role: string) => {
    switch (role) {
      case "admin":
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        )
      case "teacher":
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        )
      default:
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        )
    }
  }

  if (authLoading || bootstrapping) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white/50 text-sm">
            {bootstrapping ? "Setting up admin access..." : "Loading..."}
          </p>
        </div>
      </main>
    )
  }

  if (!user || !isAdmin) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <div className="w-16 h-16 rounded-2xl bg-red-400/10 border border-red-400/20 flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2">Admin Access Required</h1>
          <p className="text-white/50 mb-4">
            You don&apos;t have admin privileges. Only the super admin can manage users and roles.
          </p>
          {bootstrapError && (
            <p className="text-red-400/80 text-sm mb-4 bg-red-400/10 rounded-lg px-4 py-2">
              Error: {bootstrapError}
            </p>
          )}
          <p className="text-white/30 text-xs mb-6">
            Logged in as: {user?.email || "unknown"}
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-6 py-3 text-sm font-medium hover:bg-white/15 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Top bar */}
      <div className="border-b border-white/10 bg-black/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold">Admin Portal</h1>
              <p className="text-xs text-white/40">Manage users, roles &amp; access</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/teacher"
              className="hidden sm:flex items-center gap-2 rounded-lg border border-blue-400/30 bg-blue-400/10 px-4 py-2 text-sm text-blue-400 hover:bg-blue-400/20 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Upload Lectures
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-2 rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Dashboard
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-xs text-white/40 font-medium uppercase tracking-wider mb-1">Total Users</p>
            <p className="text-3xl font-bold">{stats.total}</p>
          </div>
          <div className="rounded-2xl border border-red-400/20 bg-red-400/[0.03] p-5">
            <p className="text-xs text-red-400/60 font-medium uppercase tracking-wider mb-1">Admins</p>
            <p className="text-3xl font-bold text-red-400">{stats.admins}</p>
          </div>
          <div className="rounded-2xl border border-blue-400/20 bg-blue-400/[0.03] p-5">
            <p className="text-xs text-blue-400/60 font-medium uppercase tracking-wider mb-1">Teachers</p>
            <p className="text-3xl font-bold text-blue-400">{stats.teachers}</p>
          </div>
          <div className="rounded-2xl border border-green-400/20 bg-green-400/[0.03] p-5">
            <p className="text-xs text-green-400/60 font-medium uppercase tracking-wider mb-1">Students</p>
            <p className="text-3xl font-bold text-green-400">{stats.students}</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 border-b border-white/10">
          <button
            onClick={() => setActiveTab("users")}
            className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "users"
                ? "border-white text-white"
                : "border-transparent text-white/40 hover:text-white/70"
            }`}
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              All Users
            </span>
          </button>
          <button
            onClick={() => setActiveTab("assign")}
            className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "assign"
                ? "border-white text-white"
                : "border-transparent text-white/40 hover:text-white/70"
            }`}
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
              Assign Role
            </span>
          </button>
        </div>

        {/* Users Tab */}
        {activeTab === "users" && (
          <div className="rounded-2xl border border-white/10 bg-white/[0.02]">
            {/* Search + Refresh header */}
            <div className="p-5 border-b border-white/10 flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <div className="relative flex-1 w-full">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, email, or role..."
                  className="w-full rounded-xl border border-white/10 bg-white/5 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-transparent"
                />
              </div>
              <button
                onClick={fetchUsers}
                disabled={loading}
                className="shrink-0 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm hover:bg-white/10 transition-colors disabled:opacity-50"
              >
                <svg className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>

            {/* User list */}
            {loading ? (
              <div className="p-12 text-center">
                <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-white/40">Loading users...</p>
              </div>
            ) : filteredUsers.length === 0 ? (
              <div className="p-12 text-center">
                <svg className="w-12 h-12 text-white/10 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <p className="text-sm text-white/40">No users found</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {/* Table header */}
                <div className="hidden md:grid grid-cols-12 gap-4 px-5 py-3 text-xs text-white/30 font-medium uppercase tracking-wider">
                  <div className="col-span-4">User</div>
                  <div className="col-span-3">Email</div>
                  <div className="col-span-2">Joined</div>
                  <div className="col-span-3">Role</div>
                </div>

                {filteredUsers.map((u) => (
                  <div
                    key={u.id}
                    className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-5 py-4 hover:bg-white/[0.02] transition-colors items-center"
                  >
                    {/* Name + avatar */}
                    <div className="md:col-span-4 flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-xs font-semibold shrink-0">
                        {u.full_name
                          ? u.full_name
                              .split(" ")
                              .map((n) => n[0])
                              .join("")
                              .toUpperCase()
                              .slice(0, 2)
                          : "?"}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">
                          {u.full_name || "No name"}
                        </p>
                        <p className="text-xs text-white/30 md:hidden truncate">{u.email}</p>
                      </div>
                    </div>

                    {/* Email */}
                    <div className="hidden md:block md:col-span-3">
                      <p className="text-sm text-white/60 truncate">{u.email}</p>
                    </div>

                    {/* Joined date */}
                    <div className="hidden md:block md:col-span-2">
                      <p className="text-sm text-white/40">
                        {new Date(u.created_at).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </p>
                    </div>

                    {/* Role selector */}
                    <div className="md:col-span-3 flex items-center gap-2">
                      <span className={`flex items-center gap-1.5 shrink-0 ${roleColor(u.role)} px-2 py-0.5 rounded-md border text-xs`}>
                        {roleIcon(u.role)}
                      </span>
                      <select
                        value={u.role}
                        onChange={(e) => handleInlineRoleChange(u, e.target.value)}
                        disabled={changingRole === u.id}
                        className="flex-1 min-w-0 rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/20 disabled:opacity-50 cursor-pointer"
                      >
                        <option value="student" className="bg-black">Student</option>
                        <option value="teacher" className="bg-black">Teacher</option>
                        <option value="admin" className="bg-black">Admin</option>
                      </select>
                      {changingRole === u.id && (
                        <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin shrink-0" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Footer */}
            <div className="p-4 border-t border-white/10 text-xs text-white/30 text-center">
              Showing {filteredUsers.length} of {users.length} users
            </div>
          </div>
        )}

        {/* Assign Role Tab */}
        {activeTab === "assign" && (
          <div className="max-w-lg mx-auto">
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Assign Role by Email</h2>
                  <p className="text-xs text-white/40">Enter a registered user&apos;s email to change their role</p>
                </div>
              </div>

              <form onSubmit={handleAssignRole} className="space-y-5">
                <div>
                  <label className="block text-sm text-white/60 mb-2 font-medium">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm text-white/60 mb-2 font-medium">New Role</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(["student", "teacher", "admin"] as const).map((role) => (
                      <button
                        key={role}
                        type="button"
                        onClick={() => setRoleToAssign(role)}
                        className={`flex flex-col items-center gap-1.5 rounded-xl border p-4 text-sm font-medium transition-all ${
                          roleToAssign === role
                            ? `${roleColor(role)} ring-2 ring-offset-1 ring-offset-black ${
                                role === "admin"
                                  ? "ring-red-400/40"
                                  : role === "teacher"
                                  ? "ring-blue-400/40"
                                  : "ring-green-400/40"
                              }`
                            : "border-white/10 text-white/40 hover:bg-white/5"
                        }`}
                      >
                        {roleIcon(role)}
                        <span className="capitalize">{role}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-xl px-4 py-3">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {error}
                  </div>
                )}
                {success && (
                  <div className="flex items-center gap-2 text-sm text-green-400 bg-green-400/10 border border-green-400/20 rounded-xl px-4 py-3">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {success}
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full rounded-xl bg-white text-black py-3 text-sm font-semibold hover:bg-white/90 transition-colors"
                >
                  Assign Role
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
