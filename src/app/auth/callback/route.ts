// src/app/auth/callback/route.ts
// CRITICAL: This route exchanges the OAuth code for a session and sets
// auth cookies directly on the redirect response. Using NextRequest/
// NextResponse ensures cookies survive the redirect (next/headers
// cookies().set() does NOT propagate to NextResponse.redirect()).
import { type NextRequest, NextResponse } from "next/server"
import { createServerClient } from "@supabase/ssr"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const code = url.searchParams.get("code")
  const next = url.searchParams.get("next") || "/dashboard"

  // Build the redirect response FIRST so we can attach cookies to it
  const redirectTo = new URL(next, url.origin)

  if (code) {
    const response = NextResponse.redirect(redirectTo)

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll()
          },
          setAll(cookiesToSet) {
            // Write cookies onto the outgoing redirect response
            cookiesToSet.forEach(({ name, value, options }) => {
              response.cookies.set(name, value, options)
            })
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return response // cookies are attached
    }

    // Exchange failed — redirect to login with error
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(error.message)}`, url.origin)
    )
  }

  // No code param — just redirect
  return NextResponse.redirect(redirectTo)
}
