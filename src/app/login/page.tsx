"use client"
import { supabase } from "@/lib/supabaseClient"
import { useCallback, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Suspense } from "react"

function LoginForm() {
  const searchParams = useSearchParams()
  const nextUrl = searchParams.get("next") || "/dashboard"
  const [mode, setMode] = useState<"signin" | "signup">("signin")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [fullName, setFullName] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)

  const signInWithGoogle = useCallback(async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextUrl)}` },
    })
  }, [nextUrl])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess("")
    setLoading(true)

    if (mode === "signup") {
      if (!fullName.trim()) {
        setError("Please enter your full name")
        setLoading(false)
        return
      }
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName.trim() },
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextUrl)}`,
        },
      })
      if (signUpError) {
        setError(signUpError.message)
      } else {
        setSuccess("Check your email for a confirmation link! You can also sign in with Google.")
      }
    } else {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (signInError) {
        setError(signInError.message)
      } else {
        // Sync cookies to the server before redirect
        await fetch("/api/auth/refresh", { method: "POST" }).catch(() => {})
        window.location.href = nextUrl
      }
    }
    setLoading(false)
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-8 max-w-md w-full">
      <div className="text-center mb-6">
        <Link href="/" className="text-3xl font-bold">GradeMax</Link>
        <p className="text-white/60 text-sm mt-2">
          {mode === "signin" ? "Welcome back! Sign in to continue." : "Create your account to get started."}
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex rounded-lg bg-white/5 p-1 mb-6">
        <button
          onClick={() => { setMode("signin"); setError(""); setSuccess("") }}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            mode === "signin" ? "bg-white text-black" : "text-white/70 hover:text-white"
          }`}
        >
          Sign In
        </button>
        <button
          onClick={() => { setMode("signup"); setError(""); setSuccess("") }}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            mode === "signup" ? "bg-white text-black" : "text-white/70 hover:text-white"
          }`}
        >
          Sign Up
        </button>
      </div>

      {/* Google button */}
      <button
        onClick={signInWithGoogle}
        className="w-full flex items-center justify-center gap-3 rounded-lg border border-white/20 bg-white/5 py-2.5 text-sm font-medium hover:bg-white/10 transition-colors mb-4"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Continue with Google
      </button>

      {/* Divider */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-px bg-white/10" />
        <span className="text-xs text-white/40 uppercase">or</span>
        <div className="flex-1 h-px bg-white/10" />
      </div>

      {/* Email/Password form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "signup" && (
          <div>
            <label className="block text-sm text-white/70 mb-1">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your full name"
              className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm placeholder:text-white/30 focus:outline-none focus:border-white/30"
              required
            />
          </div>
        )}

        <div>
          <label className="block text-sm text-white/70 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm placeholder:text-white/30 focus:outline-none focus:border-white/30"
            required
          />
        </div>

        <div>
          <label className="block text-sm text-white/70 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 6 characters"
            minLength={6}
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm placeholder:text-white/30 focus:outline-none focus:border-white/30"
            required
          />
        </div>

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-sm text-emerald-400">
            {success}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-white text-black py-2.5 font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {loading ? "Please wait..." : mode === "signin" ? "Sign In" : "Create Account"}
        </button>
      </form>

      {mode === "signin" && (
        <p className="mt-4 text-center text-sm text-white/50">
          Don&apos;t have an account?{" "}
          <button onClick={() => setMode("signup")} className="text-white underline underline-offset-4">
            Sign up
          </button>
        </p>
      )}
      {mode === "signup" && (
        <p className="mt-4 text-center text-sm text-white/50">
          Already have an account?{" "}
          <button onClick={() => setMode("signin")} className="text-white underline underline-offset-4">
            Sign in
          </button>
        </p>
      )}
    </div>
  )
}

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-black text-white grid place-items-center p-6">
      <Suspense fallback={
        <div className="rounded-2xl border border-white/10 bg-white/5 p-8 max-w-md w-full text-center">
          <p className="text-white/60">Loading...</p>
        </div>
      }>
        <LoginForm />
      </Suspense>
    </main>
  )
}

