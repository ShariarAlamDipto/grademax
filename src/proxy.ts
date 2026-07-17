import { NextResponse, type NextRequest } from "next/server"
import { createServerClient } from "@supabase/ssr"
import { isPublicToolsTrialActive } from "@/lib/publicToolsTrial"

// ─────────────────────────────────────────────────────────────────────────────
// Canonicalization (SEO). Runs before auth so a non-canonical URL 301s in a
// single hop without any Supabase work.
//
// Host canonicalization (apex grademax.me → www.grademax.me) is enforced by Vercel
// at the domain level, so this proxy MUST NOT touch the host — doing www→apex here
// would fight Vercel's apex→www redirect and create an infinite redirect loop.
//
// What remains: the past-paper routes force lowercase seasons and set
// `dynamicParams=false`, so historically-indexed capitalized URLs (…/2025/May-Jun)
// now hard-404. Those earned the ranking, so we 301 them to their lowercase
// canonical (same host) to preserve and consolidate the equity. Query strings are
// preserved (we clone nextUrl). Scoped to /past-papers/* whose only valid segments
// (slug, year, season, paper-N) are all lowercase.
// ─────────────────────────────────────────────────────────────────────────────
function canonicalRedirect(request: NextRequest): NextResponse | null {
  const url = request.nextUrl.clone()
  if (
    url.pathname.startsWith("/past-papers/") &&
    url.pathname !== url.pathname.toLowerCase()
  ) {
    url.pathname = url.pathname.toLowerCase()
    return NextResponse.redirect(url, 301)
  }
  return null
}

export async function proxy(request: NextRequest) {
  // The MCP connector (/api/mcp) is a POST-based JSON-RPC endpoint with its own
  // (currently anonymous) auth model. It must never be redirected or have
  // Supabase cookie work run against it — a 301/308 on a POST silently breaks
  // MCP clients. Bypass everything below.
  if (request.nextUrl.pathname.startsWith("/api/mcp")) {
    return NextResponse.next({ request: { headers: request.headers } })
  }

  // Canonicalize /past-papers/* path casing first — a single same-host 301.
  const canonical = canonicalRedirect(request)
  if (canonical) return canonical

  // Create a response we can mutate
  const response = NextResponse.next({
    request: { headers: request.headers },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          // Write into the request so downstream server components can read them
          cookiesToSet.forEach(({ name, value }) => {
            request.cookies.set(name, value)
          })
          // Write into the response so the browser stores them
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  // IMPORTANT: always call getUser() so the session gets refreshed
  // and cookies are written. Do NOT use getSession() — it doesn't
  // validate the JWT with the Supabase Auth server.
  // /generate is public while the free-access trial runs (see publicToolsTrial.ts)
  const protectedPaths = isPublicToolsTrialActive()
    ? ["/dashboard", "/profile", "/admin", "/lectures"]
    : ["/dashboard", "/profile", "/generate", "/admin", "/lectures"]
  const isProtected = protectedPaths.some((p) =>
    request.nextUrl.pathname.startsWith(p)
  )
  const isLoginPage = request.nextUrl.pathname === "/login"

  // Skip non-protected pages. API routes handle their own auth internally.
  if (!isProtected && !isLoginPage) {
    return response
  }

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Protected routes — redirect to login if not authenticated
  if (isProtected && !user) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("next", request.nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  // If logged in and visiting /login, redirect to dashboard
  if (user && isLoginPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  return response
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
}
