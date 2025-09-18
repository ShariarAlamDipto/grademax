"use client"
import { useEffect } from "react"
import { supabase } from "@/lib/supabaseClient"

export default function SupabaseAuthSync() {
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async () => {
      // Ping a no-op route to ensure cookies refresh on the server
      await fetch("/api/auth/refresh", { method: "POST" })
    })
    return () => subscription.unsubscribe()
  }, [])
  return null
}
