import { NextResponse } from "next/server"
import { headers } from "next/headers"
import { createClient } from "@supabase/supabase-js"
import { getSupabaseServer } from "./supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "./supabaseAdmin"
import type { SupabaseClient, User } from "@supabase/supabase-js"

type AuthResult =
  | { error: NextResponse }
  | { user: User; db: SupabaseClient; supabase: SupabaseClient }

type TeacherResult =
  | { error: NextResponse }
  | { user: User; db: SupabaseClient; supabase: SupabaseClient; role: string }

/**
 * Try to authenticate via Bearer token (for mobile apps).
 * Returns the user AND the authenticated client if valid, null otherwise.
 */
async function tryBearerAuth(): Promise<{ user: User; client: SupabaseClient } | null> {
  try {
    const h = await headers()
    const auth = h.get("authorization") || ""
    if (!auth.startsWith("Bearer ")) return null
    const token = auth.slice(7)
    if (!token) return null

    // Create a one-off client with the user's access token
    const client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      { global: { headers: { Authorization: `Bearer ${token}` } } }
    )
    const { data: { user } } = await client.auth.getUser(token)
    if (!user) return null
    return { user, client }
  } catch {
    return null
  }
}

/**
 * Authenticate the current request. Supports both cookie auth (web) and
 * Bearer token auth (mobile app). Returns the user and a database client
 * (admin if available, else regular). Eliminates repeated auth boilerplate.
 */
export async function requireAuth(): Promise<AuthResult> {
  // Try cookie-based auth first (web)
  const supabase = getSupabaseServer()
  let user: User | null = null

  const { data } = await supabase.auth.getUser()
  user = data.user

  // Fallback: Bearer token auth (mobile)
  let bearerClient: SupabaseClient | null = null
  if (!user) {
    const bearer = await tryBearerAuth()
    if (bearer) {
      user = bearer.user
      bearerClient = bearer.client
    }
  }

  if (!user) {
    return { error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) }
  }
  const admin = getSupabaseAdmin()
  // Prefer admin (bypasses RLS), then Bearer-authenticated client, then cookie client
  const db = admin || bearerClient || supabase
  return { user, db, supabase: bearerClient || supabase }
}

/**
 * Authenticate and verify the user is a teacher or admin.
 */
export async function requireTeacher(): Promise<TeacherResult> {
  const result = await requireAuth()
  if ("error" in result) return result
  const { user, db, supabase } = result

  const { data: profile } = await db
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  const role = profile?.role || "student"
  const isTeacherOrAdmin =
    isSuperAdmin(user.email) ||
    ["teacher", "admin"].includes(role)

  if (!isTeacherOrAdmin) {
    return { error: NextResponse.json({ error: "Forbidden" }, { status: 403 }) }
  }
  return { user, db, supabase, role }
}

/**
 * Authenticate and verify the user is an admin (or super admin by email).
 */
export async function requireAdmin(): Promise<TeacherResult> {
  const result = await requireAuth()
  if ("error" in result) return result
  const { user, db, supabase } = result

  if (isSuperAdmin(user.email)) {
    return { user, db, supabase, role: "admin" }
  }

  const { data: profile } = await db
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  if (profile?.role !== "admin") {
    return { error: NextResponse.json({ error: "Admin access required" }, { status: 403 }) }
  }
  return { user, db, supabase, role: "admin" }
}
