// src/app/auth/callback/route.ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

export const runtime = "nodejs";       // ensure Node runtime (not edge)
export const dynamic = "force-dynamic"; // avoid caching this exchange

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") || "/dashboard";

  if (code) {
    // ⬇️ Next 15 route handlers: cookies() is async
    const cookieStore = await cookies();

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get(name) {
            return cookieStore.get(name)?.value;
          },
          set(name, value, options) {
            // CRITICAL: Properly set cookies with correct options for Next.js
            try {
              cookieStore.set({
                name,
                value,
                ...options,
                sameSite: 'lax',
                httpOnly: false, // Allow client-side access
                secure: process.env.NODE_ENV === 'production',
                path: '/',
              });
            } catch (error) {
              // If set fails, cookies are read-only in this context
              console.error('Failed to set cookie:', name, error);
            }
          },
          remove(name, options) {
            try {
              cookieStore.set({
                name,
                value: "",
                ...options,
                maxAge: 0,
                path: '/',
              });
            } catch (error) {
              console.error('Failed to remove cookie:', name, error);
            }
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      console.error('OAuth callback error:', error);
      return NextResponse.redirect(
        `${url.origin}/login?error=${encodeURIComponent(error.message)}`
      );
    }

    // After successful auth, redirect with proper response
    const response = NextResponse.redirect(`${url.origin}${next}`);
    
    // Ensure cookies are set in the response headers
    return response;
  }

  // No code provided, redirect to login
  return NextResponse.redirect(`${url.origin}/login`);
}
