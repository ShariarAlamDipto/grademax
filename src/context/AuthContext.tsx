"use client"
import { createContext, useContext, useEffect, useState, useCallback } from "react"
import { supabase } from "@/lib/supabaseClient"
import type { User, Session } from "@supabase/supabase-js"

interface Profile {
  id: string
  email: string | null
  full_name: string | null
  avatar_url: string | null
  study_level: string | null
  marks_goal_pct: number
  role: "student" | "teacher" | "admin"
}

interface AuthContextType {
  user: User | null
  session: Session | null
  profile: Profile | null
  loading: boolean
  displayName: string
  avatarUrl: string | null
  refreshProfile: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  profile: null,
  loading: true,
  displayName: "",
  avatarUrl: null,
  refreshProfile: async () => {},
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchProfileDirect = useCallback(async (userId: string) => {
    const { data } = await supabase
      .from("profiles")
      .select("id, email, full_name, avatar_url, study_level, marks_goal_pct, role")
      .eq("id", userId)
      .single()
    setProfile(data ? { ...data, role: data.role || "student" } : null)
  }, [])

  const refreshProfile = useCallback(async () => {
    if (user?.id) {
      await fetchProfileDirect(user.id)
    }
  }, [user?.id, fetchProfileDirect])

  useEffect(() => {
    let bootstrapped = false
    let resolved = false

    // Safety-net: guarantee loading becomes false within 5s even if
    // onAuthStateChange never fires (e.g. stale cookies, network issues).
    const timeout = setTimeout(() => {
      if (!resolved) {
        resolved = true
        setLoading(false)
      }
    }, 5000)

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, s) => {
        // Only sync cookies on sign-in and token refresh
        if (s?.user && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) {
          fetch("/api/auth/refresh", { method: "POST" }).catch(() => {})
        }

        if (s?.user) {
          // Bootstrap admin once per session — fire-and-forget with short timeout
          if (!bootstrapped && s.user.email?.toLowerCase() === "shariardipto111@gmail.com") {
            bootstrapped = true
            try {
              await Promise.race([
                fetch("/api/admin/bootstrap", { method: "POST" }),
                new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 3000)),
              ])
            } catch {}
          }
          // Fetch profile AFTER bootstrap so the role is up-to-date
          try {
            await fetchProfileDirect(s.user.id)
          } catch {
            setProfile(null)
          }
        } else {
          setProfile(null)
        }
        // Only set user/session AFTER profile is fetched
        setSession(s)
        setUser(s?.user ?? null)
        if (!resolved) {
          resolved = true
          setLoading(false)
        }

        // After SIGNED_IN event, if we're still on /login, navigate to dashboard
        if (s?.user && event === "SIGNED_IN" && window.location.pathname === "/login") {
          const params = new URLSearchParams(window.location.search)
          window.location.href = params.get("next") || "/dashboard"
        }
      }
    )

    return () => {
      clearTimeout(timeout)
      subscription.unsubscribe()
    }
  }, [fetchProfileDirect])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    setUser(null)
    setSession(null)
    setProfile(null)
    window.location.href = "/"
  }, [])

  const displayName =
    profile?.full_name ||
    (user?.user_metadata?.full_name as string) ||
    (user?.user_metadata?.name as string) ||
    user?.email?.split("@")[0] ||
    ""

  const avatarUrl =
    profile?.avatar_url ||
    (user?.user_metadata?.avatar_url as string) ||
    null

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        loading,
        displayName,
        avatarUrl,
        refreshProfile,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
