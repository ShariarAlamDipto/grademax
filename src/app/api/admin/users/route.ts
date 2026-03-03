import { NextRequest, NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"

// GET /api/admin/users - List all users with their roles (admin only)
export async function GET() {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  if (!profile || profile.role !== "admin") {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 })
  }

  const { data: users, error } = await supabase
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
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  if (!profile || profile.role !== "admin") {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 })
  }

  const body = await req.json()
  const { email, role } = body

  if (!email || !role || !["student", "teacher", "admin"].includes(role)) {
    return NextResponse.json({ error: "Valid email and role (student/teacher/admin) required" }, { status: 400 })
  }

  const { data: targetUser, error: findError } = await supabase
    .from("profiles")
    .select("id, email, role")
    .eq("email", email)
    .single()

  if (findError || !targetUser) {
    return NextResponse.json({ error: "User not found with that email" }, { status: 404 })
  }

  const { error: updateError } = await supabase
    .from("profiles")
    .update({ role })
    .eq("id", targetUser.id)

  if (updateError) {
    return NextResponse.json({ error: updateError.message }, { status: 500 })
  }

  return NextResponse.json({ success: true, user: { ...targetUser, role } })
}
