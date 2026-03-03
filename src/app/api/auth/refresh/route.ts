import { type NextRequest, NextResponse } from "next/server"
import { createServerClient } from "@supabase/ssr"

// Refresh the auth session and ensure cookies are properly propagated
// Uses NextRequest/NextResponse pattern to ensure cookies survive
async function refreshSession(request: NextRequest) {
  const response = NextResponse.json({ ok: true })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          // Write cookies onto the outgoing response
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()
  return NextResponse.json({ ok: true, authenticated: !!user }, {
    headers: response.headers,
  })
}

export async function POST(request: NextRequest) {
  return refreshSession(request)
}

export async function GET(request: NextRequest) {
  return refreshSession(request)
}
