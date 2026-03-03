import { NextResponse } from "next/server"
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
 * Authenticate the current request. Returns the user and a database client
 * (admin if available, else regular). Eliminates repeated auth boilerplate.
 */
export async function requireAuth(): Promise<AuthResult> {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return { error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) }
  }
  const admin = getSupabaseAdmin()
  const db = admin || supabase
  return { user, db, supabase }
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
