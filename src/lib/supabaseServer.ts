import { cookies } from "next/headers"
// If you see a module error, run: npm install @supabase/ssr
import { createServerClient } from "@supabase/ssr"

export function getSupabaseServer() {
  const cookieStore = cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get: async (name: string) => {
          const store = await cookieStore;
          return store.get(name)?.value;
        },
        set: async (name: string, value: string, options: Record<string, unknown>) => {
          const store = await cookieStore;
          store.set(name, value, options);
        },
        remove: async (name: string, options: Record<string, unknown>) => {
          const store = await cookieStore;
          store.set(name, "", { ...options, maxAge: 0 });
        },
      },
    }
  )
}
