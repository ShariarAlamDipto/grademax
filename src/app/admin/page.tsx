"use client"
import { useAuth } from "@/context/AuthContext"
import { useState, useEffect, useCallback } from "react"
import Link from "next/link"

interface UserEntry {
  id: string
  email: string | null
  full_name: string | null
  role: string
  created_at: string
}

export default function AdminPage() {
  const { user, profile, loading: authLoading } = useAuth()
  const [users, setUsers] = useState<UserEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState("")
  const [roleToAssign, setRoleToAssign] = useState<"student" | "teacher" | "admin">("teacher")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [searchQuery, setSearchQuery] = useState("")

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    const res = await fetch("/api/admin/users")
    if (res.ok) {
      const data = await res.json()
      setUsers(data.users || [])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (user && profile?.role === "admin") {
      fetchUsers()
    }
  }, [user, profile?.role, fetchUsers])

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

  const filteredUsers = users.filter((u) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      u.email?.toLowerCase().includes(q) ||
      u.full_name?.toLowerCase().includes(q) ||
      u.role.toLowerCase().includes(q)
    )
  })

  const roleColor = (role: string) => {
    switch (role) {
      case "admin": return "text-red-400 bg-red-400/10 border-red-400/20"
      case "teacher": return "text-blue-400 bg-blue-400/10 border-blue-400/20"
      default: return "text-green-400 bg-green-400/10 border-green-400/20"
    }
  }

  if (authLoading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="animate-pulse text-white/50">Loading...</div>
      </main>
    )
  }

  if (!user || !profile || profile.role !== "admin") {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-4xl mb-4">🔒</div>
          <h1 className="text-xl font-bold mb-2">Admin Access Required</h1>
          <p className="text-white/60 mb-4">
            You need admin privileges to manage users and roles.
          </p>
          <Link href="/dashboard" className="rounded-lg bg-white/10 px-6 py-2 text-sm hover:bg-white/15">
            Back to Dashboard
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      <div className="max-w-4xl mx-auto py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">Admin Panel</h1>
            <p className="text-sm text-white/50 mt-1">Manage user roles and access</p>
          </div>
          <Link
            href="/dashboard"
            className="rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
          >
            Dashboard
          </Link>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Assign Role Panel */}
          <div className="lg:col-span-1">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-lg font-semibold mb-4">Assign Role</h2>
              <p className="text-xs text-white/40 mb-4">
                Enter the user&apos;s email to assign them a role. They must already have an account.
              </p>

              <form onSubmit={handleAssignRole} className="space-y-4">
                <div>
                  <label className="block text-sm text-white/70 mb-1">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teacher@example.com"
                    className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-white/30"
                  />
                </div>

                <div>
                  <label className="block text-sm text-white/70 mb-1">Role</label>
                  <select
                    value={roleToAssign}
                    onChange={(e) => setRoleToAssign(e.target.value as "student" | "teacher" | "admin")}
                    className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/30"
                  >
                    <option value="student" className="bg-black">Student</option>
                    <option value="teacher" className="bg-black">Teacher</option>
                    <option value="admin" className="bg-black">Admin</option>
                  </select>
                </div>

                {error && <p className="text-sm text-red-400">{error}</p>}
                {success && <p className="text-sm text-green-400">{success}</p>}

                <button
                  type="submit"
                  className="w-full rounded-lg bg-white text-black py-2.5 text-sm font-medium hover:bg-white/90 transition-colors"
                >
                  Assign Role
                </button>
              </form>
            </div>
          </div>

          {/* Users List */}
          <div className="lg:col-span-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">All Users</h2>
                <span className="text-sm text-white/40">{users.length} users</span>
              </div>

              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search users..."
                className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-white/30 mb-4 focus:outline-none focus:ring-2 focus:ring-white/30"
              />

              {loading ? (
                <div className="text-center py-8">
                  <div className="animate-pulse text-white/50">Loading users...</div>
                </div>
              ) : filteredUsers.length === 0 ? (
                <p className="text-sm text-white/40 text-center py-8">No users found</p>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {filteredUsers.map((u) => (
                    <div
                      key={u.id}
                      className="flex items-center justify-between rounded-lg bg-white/[0.03] border border-white/5 px-4 py-3"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{u.full_name || "—"}</p>
                        <p className="text-xs text-white/40 truncate">{u.email}</p>
                      </div>
                      <span
                        className={`shrink-0 ml-3 text-xs px-2.5 py-1 rounded-full border font-medium ${roleColor(u.role)}`}
                      >
                        {u.role}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
