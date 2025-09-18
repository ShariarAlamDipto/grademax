import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"

export async function GET(request: Request) {
  const url = new URL(request.url)
  const code = url.searchParams.get("code")

  if (code) {
    const cookieStorePromise = cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get: async (name: string) => {
            const store = await cookieStorePromise;
            return store.get(name)?.value;
          },
          set: async (name: string, value: string, options: Record<string, unknown>) => {
            const store = await cookieStorePromise;
            store.set(name, value, options);
          },
          remove: async (name: string, options: Record<string, unknown>) => {
            const store = await cookieStorePromise;
            store.set(name, "", { ...options, maxAge: 0 });
          },
        },
      }
    );
    await supabase.auth.exchangeCodeForSession(code);
  }
  return NextResponse.redirect(`${url.origin}/dashboard`)
}
