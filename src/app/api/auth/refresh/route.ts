import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"

async function refreshSession() {
  const cookieStore = await cookies()

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options)
            })
          } catch {
            // setAll may throw in some contexts; safe to ignore
          }
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()
  return NextResponse.json({ ok: true, authenticated: !!user })
}

export async function POST() {
  return refreshSession()
}

// Also handle GET so the browser can refresh via a simple fetch or navigation
export async function GET() {
  return refreshSession()
}
