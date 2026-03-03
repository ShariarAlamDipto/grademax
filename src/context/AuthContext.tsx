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

  const fetchProfile = useCallback(async (userId: string, userEmail?: string) => {
    // If this is the super admin, auto-bootstrap their role first
    if (userEmail && userEmail.toLowerCase() === "shariardipto111@gmail.com") {
      await fetch("/api/admin/bootstrap", { method: "POST" }).catch(() => {})
    }

    const { data } = await supabase
      .from("profiles")
      .select("id, email, full_name, avatar_url, study_level, marks_goal_pct, role")
      .eq("id", userId)
      .single()
    setProfile(data ? { ...data, role: data.role || "student" } : null)
  }, [])

  const refreshProfile = useCallback(async () => {
    if (user?.id) {
      await fetchProfile(user.id, user.email ?? undefined)
    }
  }, [user?.id, user?.email, fetchProfile])

  useEffect(() => {
    // Get initial session
    const init = async () => {
      const { data: { session: s } } = await supabase.auth.getSession()
      setSession(s)
      setUser(s?.user ?? null)
      if (s?.user) {
        // Sync cookies to the server immediately
        await fetch("/api/auth/refresh", { method: "POST" }).catch(() => {})
        await fetchProfile(s.user.id, s.user.email ?? undefined)
      }
      setLoading(false)
    }
    init()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, s) => {
        setSession(s)
        setUser(s?.user ?? null)
        if (s?.user) {
          // Sync cookies to the server FIRST so server components can read them
          await fetch("/api/auth/refresh", { method: "POST" }).catch(() => {})
          await fetchProfile(s.user.id, s.user.email ?? undefined)

          // After SIGNED_IN event, if we're still on /login, navigate to dashboard
          if (event === "SIGNED_IN" && window.location.pathname === "/login") {
            const params = new URLSearchParams(window.location.search)
            const next = params.get("next") || "/dashboard"
            window.location.href = next
            return
          }
        } else {
          setProfile(null)
        }
        setLoading(false)
      }
    )

    return () => subscription.unsubscribe()
  }, [fetchProfile])

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
