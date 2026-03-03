import { createClient, SupabaseClient } from "@supabase/supabase-js"

/**
 * Supabase client with service_role key — bypasses RLS.
 * ONLY use this in server-side API routes, NEVER expose to the client.
 * Cached as a singleton to avoid recreating the client on every call.
 */
let _adminClient: SupabaseClient | null | undefined

export function getSupabaseAdmin(): SupabaseClient | null {
  if (_adminClient !== undefined) return _adminClient

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!url || !serviceKey) {
    _adminClient = null
    return null
  }

  _adminClient = createClient(url, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  })
  return _adminClient
}

/**
 * Super admin email — this account is automatically promoted to admin+teacher
 * on every login. No database changes needed.
 */
export const SUPER_ADMIN_EMAIL = "shariardipto111@gmail.com"

/**
 * Check if an email is the super admin
 */
export function isSuperAdmin(email: string | undefined | null): boolean {
  if (!email) return false
  return email.toLowerCase() === SUPER_ADMIN_EMAIL.toLowerCase()
}
