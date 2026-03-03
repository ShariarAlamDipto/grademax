import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getSupabaseServer } from "@/lib/supabaseServer"

// GET /api/admin/users - List all users with their roles (admin only)
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error
  const { db } = auth

  const { data: users, error } = await db
    .from("profiles")
    .select("id, email, full_name, role, created_at")
    .order("created_at", { ascending: false })

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ users })
}

// PATCH /api/admin/users - Update a user's role by email (admin only)
export async function PATCH(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error
  const { db } = auth

  const body = await req.json()
  const { email, role } = body

  if (!email || !role || !["student", "teacher", "admin"].includes(role)) {
    return NextResponse.json({ error: "Valid email and role (student/teacher/admin) required" }, { status: 400 })
  }

  const { data: targetUser, error: findError } = await db
    .from("profiles")
    .select("id, email, role")
    .eq("email", email)
    .single()

  if (findError || !targetUser) {
    return NextResponse.json({ error: "User not found with that email" }, { status: 404 })
  }

  const { error: updateError } = await db
    .from("profiles")
    .update({ role })
    .eq("id", targetUser.id)

  if (updateError) {
    return NextResponse.json({ error: updateError.message }, { status: 500 })
  }

  return NextResponse.json({ success: true, user: { ...targetUser, role } })
}
