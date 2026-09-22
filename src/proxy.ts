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
// preserved (we clone nextUrl).
//
// Two classes of near-miss URL reach us and hard-404 today:
//
//  1. Casing — /Edexcel-A-Level-Past-Papers, /past-papers/…/May-Jun. Every one of
//     the 15,059 URLs we publish in sitemap.xml is entirely lowercase, so for the
//     prefixes below lowercase is provably the canonical form.
//  2. Unicode dashes — U+2010‑U+2015 and U+2212. Chat assistants, Word/Docs
//     "smart" autoformatting and PDF copy-paste silently rewrite the ASCII
//     hyphen, producing links like /edexcel%E2%80%91a%E2%80%91level%E2%80%91past%E2%80%91papers
//     (U+2011 NON-BREAKING HYPHEN) that look identical to a human but 404. These
//     are shared and clicked by real users, so we repair rather than reject them.
//
// Both are folded into a SINGLE 301 so a doubly-malformed URL never chains two
// hops. Normalization is idempotent — the output holds no unicode dash and no
// uppercase — so a redirect loop is not reachable.
// ─────────────────────────────────────────────────────────────────────────────
const CANONICAL_LOWERCASE_PREFIXES = [
  "/past-papers",
  "/subjects",
  "/qp",
  "/edexcel-past-papers",
  "/edexcel-igcse-past-papers",
  "/edexcel-a-level-past-papers",
  "/edexcel-worksheets",
  "/cambridge-past-papers",
  "/cambridge-igcse-past-papers",
  "/cambridge-a-level-past-papers",
  "/browse",
  "/test-builder",
  "/about",
  "/contact",
  "/privacy",
  "/terms",
] as const

// U+2010 HYPHEN, U+2011 NON-BREAKING HYPHEN, U+2012 FIGURE DASH, U+2013 EN DASH,
// U+2014 EM DASH, U+2015 HORIZONTAL BAR, U+2212 MINUS SIGN.
const UNICODE_DASH_RE = /[‐-―−]/g

/** Decode a percent-encoded pathname, falling back to the raw value if malformed. */
function safeDecodePathname(pathname: string): string {
  try {
    return decodeURIComponent(pathname)
  } catch {
    return pathname
  }
}

function canonicalPathname(pathname: string): string {
  return safeDecodePathname(pathname).replace(UNICODE_DASH_RE, "-").toLowerCase()
}

function canonicalRedirect(request: NextRequest): NextResponse | null {
  const url = request.nextUrl.clone()
  const canonical = canonicalPathname(url.pathname)
  if (canonical === url.pathname) return null

  // Only redirect into route families whose canonical form we can guarantee.
  // Matching on the *normalized* path is what lets a mangled prefix such as
  // "/edexcel‑a‑level‑past‑papers" be recognised in the first place.
  const isCanonicalisable = CANONICAL_LOWERCASE_PREFIXES.some(
    (prefix) => canonical === prefix || canonical.startsWith(`${prefix}/`)
  )
  if (!isCanonicalisable) return null

  url.pathname = canonical
  return NextResponse.redirect(url, 301)
}

export async function proxy(request: NextRequest) {
  // The MCP connector (/api/mcp) is a POST-based JSON-RPC endpoint with its own
  // (currently anonymous) auth model. It must never be redirected or have
  // Supabase cookie work run against it — a 301/308 on a POST silently breaks
  // MCP clients. Bypass everything below.
  if (request.nextUrl.pathname.startsWith("/api/mcp")) {
    return NextResponse.next({ request: { headers: request.headers } })
  }

  // Canonicalize path casing + unicode dashes first — a single same-host 301.
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
