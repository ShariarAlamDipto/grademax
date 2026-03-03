import { NextResponse, type NextRequest } from "next/server"
import { createServerClient } from "@supabase/ssr"

export async function middleware(request: NextRequest) {
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
  const protectedPaths = ["/dashboard", "/profile", "/generate", "/admin", "/lectures"]
  const isProtected = protectedPaths.some((p) =>
    request.nextUrl.pathname.startsWith(p)
  )
  const isApiRoute = request.nextUrl.pathname.startsWith("/api/")
  const isLoginPage = request.nextUrl.pathname === "/login"

  // Skip Supabase call entirely for public pages (NOT api routes — those need fresh sessions)
  if (!isProtected && !isApiRoute && !isLoginPage) {
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
