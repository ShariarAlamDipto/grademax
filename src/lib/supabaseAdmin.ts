import { createClient, SupabaseClient } from "@supabase/supabase-js"

/**
 * Supabase client with service_role key — bypasses RLS.
 * ONLY use this in server-side API routes, NEVER expose to the client.
 * Cached as a singleton to avoid recreating the client on every call.
 */
let _adminClient: SupabaseClient | null = null

export function getSupabaseAdmin(): SupabaseClient | null {
  // Return cached client if already created
  if (_adminClient) return _adminClient

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  // Check multiple common env var names for the service role key
  // NOTE: Never use NEXT_PUBLIC_ prefix for service role key — it would be exposed in the client bundle
  const serviceKey =
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_SERVICE_KEY

  if (!url || !serviceKey) {
    console.warn(
      "[supabaseAdmin] Missing env vars.",
      "NEXT_PUBLIC_SUPABASE_URL:", !!url,
      "SUPABASE_SERVICE_ROLE_KEY:", !!process.env.SUPABASE_SERVICE_ROLE_KEY,
      "SUPABASE_SERVICE_KEY:", !!process.env.SUPABASE_SERVICE_KEY
    )
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
 * Check if an email is the super admin.
 * Reads from SUPER_ADMIN_EMAIL env var — never hardcoded in source.
 */
export function isSuperAdmin(email: string | undefined | null): boolean {
  if (!email) return false
  const superAdminEmail = process.env.SUPER_ADMIN_EMAIL
  if (!superAdminEmail) return false
  return email.toLowerCase() === superAdminEmail.toLowerCase()
}
