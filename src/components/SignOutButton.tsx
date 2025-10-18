"use client"

import { createClient } from "@/lib/supabaseBrowser"
import { useState } from "react"

export default function SignOutButton({ className = "" }: { className?: string }) {
  const [isSigningOut, setIsSigningOut] = useState(false)

  const handleSignOut = async () => {
    if (isSigningOut) return
    
    setIsSigningOut(true)
    
    try {
      const supabase = createClient()
      
      // 1. Sign out from Supabase (clears auth cookies)
      await supabase.auth.signOut()
      
      // 2. Clear all localStorage
      localStorage.clear()
      
      // 3. Clear all sessionStorage
      sessionStorage.clear()
      
      // 4. Clear any app-specific data
      if (typeof window !== 'undefined') {
        // Clear all cookies manually
        document.cookie.split(";").forEach((c) => {
          document.cookie = c
            .replace(/^ +/, "")
            .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/")
        })
      }
      
      // 5. Force redirect to login
      window.location.href = "/login"
    } catch (error) {
      console.error("Sign out error:", error)
      // Even if error, still redirect to login
      window.location.href = "/login"
    }
  }

  return (
    <button
      onClick={handleSignOut}
      disabled={isSigningOut}
      className={`rounded-md bg-white/10 px-3 py-1.5 text-sm hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {isSigningOut ? "Signing out..." : "Sign out"}
    </button>
  )
}
