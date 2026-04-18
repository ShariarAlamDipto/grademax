"use client"
import { useAuth } from "@/context/AuthContext"
import { supabase } from "@/lib/supabaseClient"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"

export default function ProfilePage() {
  const { user, profile, displayName, avatarUrl, loading, refreshProfile, signOut } = useAuth()
  const router = useRouter()

  // Profile editing
  const [fullName, setFullName] = useState("")
  const [studyLevel, setStudyLevel] = useState("")
  const [marksGoal, setMarksGoal] = useState(90)
  const [savingProfile, setSavingProfile] = useState(false)
  const [profileMsg, setProfileMsg] = useState("")

  // Password change
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [savingPassword, setSavingPassword] = useState(false)
  const [passwordMsg, setPasswordMsg] = useState("")
  const [passwordError, setPasswordError] = useState("")

  // Delete account
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  useEffect(() => {
    if (profile) {
      setFullName(profile.full_name || "")
      setStudyLevel(profile.study_level || "")
      setMarksGoal(profile.marks_goal_pct ?? 90)
    } else if (user) {
      setFullName(
        (user.user_metadata?.full_name as string) ||
        (user.user_metadata?.name as string) ||
        ""
      )
    }
  }, [profile, user])

  useEffect(() => {
    if (!loading && !user) router.push("/login")
  }, [loading, user, router])

  if (loading) {
    return (
      <main className="min-h-screen bg-black text-white grid place-items-center">
        <div className="text-white/60">Loading...</div>
      </main>
    )
  }

  if (!user) return null

  const isGoogleUser = user.app_metadata?.provider === "google"

  const handleSaveProfile = async () => {
    setSavingProfile(true)
    setProfileMsg("")

    // Update profile in database
    const { error } = await supabase
      .from("profiles")
      .upsert({
        id: user.id,
        full_name: fullName.trim(),
        study_level: studyLevel || null,
        marks_goal_pct: marksGoal,
        email: user.email,
      })

    if (error) {
      setProfileMsg("Error saving profile: " + error.message)
    } else {
      // Also update auth metadata
      await supabase.auth.updateUser({
        data: { full_name: fullName.trim() },
      })
      await refreshProfile()
      setProfileMsg("Profile saved successfully!")
    }
    setSavingProfile(false)
    setTimeout(() => setProfileMsg(""), 3000)
  }

  const handleChangePassword = async () => {
    setPasswordError("")
    setPasswordMsg("")

    if (newPassword.length < 6) {
      setPasswordError("Password must be at least 6 characters")
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match")
      return
    }

    setSavingPassword(true)
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    })

    if (error) {
      setPasswordError(error.message)
    } else {
      setPasswordMsg("Password updated successfully!")
      setNewPassword("")
      setConfirmPassword("")
    }
    setSavingPassword(false)
    setTimeout(() => setPasswordMsg(""), 3000)
  }

  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl md:text-3xl font-bold mb-8">My Profile</h1>

        {/* Avatar & Name Header */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 mb-6">
          <div className="flex items-center gap-4">
            {avatarUrl ? (
              <Image
                src={avatarUrl}
                alt={displayName}
                width={64}
                height={64}
                className="w-16 h-16 rounded-full object-cover border-2 border-white/20"
                referrerPolicy="no-referrer"
                unoptimized
              />
            ) : (
              <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-xl font-bold">
                {displayName
                  .split(" ")
                  .map((n) => n[0])
                  .join("")
                  .toUpperCase()
                  .slice(0, 2)}
              </div>
            )}
            <div>
              <h2 className="text-xl font-semibold">{displayName || "Student"}</h2>
              <p className="text-sm text-white/50">{user.email}</p>
              {isGoogleUser && (
                <span className="inline-flex items-center gap-1 mt-1 text-xs text-white/40 bg-white/5 rounded-full px-2 py-0.5">
                  <svg className="w-3 h-3" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/></svg>
                  Google Account
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Edit Profile Section */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Edit Profile</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-white/70 mb-1">Display Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your full name"
                className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
            </div>

            <div>
              <label className="block text-sm text-white/70 mb-1">Email</label>
              <input
                type="email"
                value={user.email || ""}
                disabled
                className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm text-white/50 cursor-not-allowed"
              />
              <p className="text-xs text-white/40 mt-1">Email cannot be changed</p>
            </div>

            <div>
              <label className="block text-sm text-white/70 mb-1">Exam Level</label>
              <div className="flex gap-2">
                {(["igcse", "ial"] as const).map((lvl) => (
                  <button
                    key={lvl}
                    onClick={() => setStudyLevel(lvl)}
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      studyLevel === lvl
                        ? "bg-white text-black border-white/20"
                        : "bg-white/5 text-white/70 border-white/10 hover:bg-white/10"
                    }`}
                  >
                    {lvl.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm text-white/70 mb-1">Marks Goal (%)</label>
              <input
                type="number"
                value={marksGoal}
                onChange={(e) => setMarksGoal(Math.max(0, Math.min(100, Number(e.target.value))))}
                className="w-28 rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm focus:outline-none focus:border-white/30"
              />
            </div>

            {profileMsg && (
              <div className={`rounded-lg p-3 text-sm ${
                profileMsg.includes("Error")
                  ? "bg-red-500/10 border border-red-500/20 text-red-400"
                  : "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
              }`}>
                {profileMsg}
              </div>
            )}

            <button
              onClick={handleSaveProfile}
              disabled={savingProfile}
              className="rounded-lg bg-white text-black px-5 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {savingProfile ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>

        {/* Change Password Section */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 mb-6">
          <h3 className="text-lg font-semibold mb-2">Change Password</h3>
          {isGoogleUser ? (
            <p className="text-sm text-white/50">
              You signed in with Google. To set a password for email-based login, enter a new password below.
            </p>
          ) : (
            <p className="text-sm text-white/50 mb-4">
              Update your account password.
            </p>
          )}

          <div className="space-y-4 mt-4">
            <div>
              <label className="block text-sm text-white/70 mb-1">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 6 characters"
                minLength={6}
                className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
            </div>

            <div>
              <label className="block text-sm text-white/70 mb-1">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat new password"
                className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
            </div>

            {passwordError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400">
                {passwordError}
              </div>
            )}
            {passwordMsg && (
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-sm text-emerald-400">
                {passwordMsg}
              </div>
            )}

            <button
              onClick={handleChangePassword}
              disabled={savingPassword || !newPassword}
              className="rounded-lg bg-white text-black px-5 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {savingPassword ? "Updating..." : "Update Password"}
            </button>
          </div>
        </div>

        {/* Account Actions */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h3 className="text-lg font-semibold mb-4">Account</h3>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={signOut}
              className="rounded-lg border border-white/20 bg-white/5 px-5 py-2 text-sm font-medium hover:bg-white/10 transition-colors"
            >
              Sign Out
            </button>

            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="rounded-lg border border-red-500/30 bg-red-500/5 px-5 py-2 text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
            >
              Delete Account
            </button>
          </div>

          {showDeleteConfirm && (
            <div className="mt-4 p-4 rounded-lg border border-red-500/20 bg-red-500/5">
              <p className="text-sm text-red-400 mb-3">
                Are you sure? This action cannot be undone. All your data will be permanently deleted.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="rounded-lg border border-white/20 bg-white/5 px-4 py-1.5 text-sm hover:bg-white/10"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    // Note: actual account deletion typically requires a server-side function
                    // For now, sign out and show message
                    alert("Please contact support to delete your account.")
                    setShowDeleteConfirm(false)
                  }}
                  className="rounded-lg bg-red-500 text-white px-4 py-1.5 text-sm hover:bg-red-600"
                >
                  Confirm Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
