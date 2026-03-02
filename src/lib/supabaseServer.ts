import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"

export function getSupabaseServer() {
  const cookieStorePromise = cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        async getAll() {
          const store = await cookieStorePromise
          return store.getAll()
        },
        async setAll(cookiesToSet) {
          try {
            const store = await cookieStorePromise
            cookiesToSet.forEach(({ name, value, options }) => {
              store.set(name, value, options)
            })
          } catch {
            // setAll is called from a Server Component —
            // this can be ignored if middleware refreshes the session.
          }
        },
      },
    }
  )
}
