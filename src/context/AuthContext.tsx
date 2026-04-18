"use client"
import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react"
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
  profileLoaded: boolean
  displayName: string
  avatarUrl: string | null
  role: "student" | "teacher" | "admin"
  isTeacher: boolean
  isAdmin: boolean
  refreshProfile: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  profile: null,
  loading: true,
  profileLoaded: false,
  displayName: "",
  avatarUrl: null,
  role: "student",
  isTeacher: false,
  isAdmin: false,
  refreshProfile: async () => {},
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [profileLoaded, setProfileLoaded] = useState(false)
  const bootstrappedRef = useRef(false)
  const initializedRef = useRef(false)

  const fetchProfileDirect = useCallback(async (userId: string, retryCount = 0) => {
    try {
      const { data, error } = await supabase
        .from("profiles")
        .select("id, email, full_name, avatar_url, study_level, marks_goal_pct, role")
        .eq("id", userId)
        .single()

      if (error) {
        console.error("[Auth] Profile fetch error:", error.message, error.code)
        if (retryCount < 2) {
          setTimeout(() => fetchProfileDirect(userId, retryCount + 1), 1500)
          return
        }
        // All retries exhausted — try server-side fallback
        try {
          const res = await fetch("/api/auth/me")
          if (res.ok) {
            const serverProfile = await res.json()
            if (serverProfile?.id) {
              setProfile({ ...serverProfile, role: serverProfile.role || "student" })
              setProfileLoaded(true)
              return
            }
          }
        } catch { /* ignore fallback errors */ }
        setProfile(null)
        setProfileLoaded(true)
        return
      }

      if (!data) {
        console.warn("[Auth] No profile found for user:", userId)
        if (retryCount < 2) {
          setTimeout(() => fetchProfileDirect(userId, retryCount + 1), 1500)
          return
        }
        setProfile(null)
        setProfileLoaded(true)
        return
      }

      setProfile({ ...data, role: data.role || "student" })
      setProfileLoaded(true)
    } catch (err) {
      console.error("[Auth] Profile fetch exception:", err)
      setProfile(null)
      setProfileLoaded(true)
    }
  }, [])

  const refreshProfile = useCallback(async () => {
    if (user?.id) {
      await fetchProfileDirect(user.id)
    }
  }, [user?.id, fetchProfileDirect])

  // Handle session changes (both from getSession and onAuthStateChange)
  const handleSession = useCallback((s: Session | null, event?: string) => {
    setSession(s)
    setUser(s?.user ?? null)

    if (s?.user) {
      // Sync server-side cookies — fire and forget
      fetch("/api/auth/refresh", { method: "POST" }).catch(() => {})

      // Bootstrap admin once per page load — fire and forget
      if (!bootstrappedRef.current && s.user.email?.toLowerCase() === process.env.NEXT_PUBLIC_SUPER_ADMIN_EMAIL?.toLowerCase()) {
        bootstrappedRef.current = true
        fetch("/api/admin/bootstrap", { method: "POST" })
          .then(() => fetchProfileDirect(s.user!.id))
          .catch(() => {})
      }

      // Fetch profile async (non-blocking)
      fetchProfileDirect(s.user.id)
    } else {
      setProfile(null)
    }

    // Redirect away from /login if authenticated
    if (
      s?.user &&
      (!event || event === "SIGNED_IN" || event === "INITIAL_SESSION" || event === "TOKEN_REFRESHED") &&
      typeof window !== "undefined" &&
      window.location.pathname === "/login"
    ) {
      const params = new URLSearchParams(window.location.search)
      window.location.href = params.get("next") || "/dashboard"
    }
  }, [fetchProfileDirect])

  useEffect(() => {
    let resolved = false

    const resolve = () => {
      if (!resolved) {
        resolved = true
        setLoading(false)
      }
    }

    // Safety-net: guarantee loading becomes false within 4s
    const timeout = setTimeout(resolve, 4000)

    // *** STRATEGY: Use BOTH getSession() (instant, local) and
    // onAuthStateChange (reactive, reliable) to ensure we never
    // miss an existing session. This prevents the "Sign In" flash. ***

    // 1. Immediately check for an existing session from cookies
    if (!initializedRef.current) {
      initializedRef.current = true
      supabase.auth.getSession().then(({ data: { session: existingSession } }) => {
        if (existingSession?.user) {
          handleSession(existingSession)
          resolve()
        }
      }).catch(() => {})
    }

    // 2. Listen for auth state changes (handles sign-in, sign-out, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, s) => {
        handleSession(s, event)
        resolve()
      }
    )

    return () => {
      clearTimeout(timeout)
      subscription.unsubscribe()
    }
  }, [handleSession])

  // Auto-refresh profile when tab becomes visible (picks up role changes from admin)
  // Throttled to once per 30s to avoid unnecessary DB round-trips
  useEffect(() => {
    let lastFetch = 0
    const onVisibilityChange = () => {
      const now = Date.now()
      if (document.visibilityState === "visible" && user?.id && now - lastFetch > 30_000) {
        lastFetch = now
        fetchProfileDirect(user.id)
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => document.removeEventListener("visibilitychange", onVisibilityChange)
  }, [user?.id, fetchProfileDirect])

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

  const role = profile?.role || "student"
  const isAdmin = role === "admin"
  const isTeacher = role === "teacher" || isAdmin

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        loading,
        profileLoaded,
        displayName,
        avatarUrl,
        role,
        isTeacher,
        isAdmin,
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
