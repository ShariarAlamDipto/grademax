import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

// GET /api/admin/users - List all users with their roles (admin only)
// Merges auth.users (email, name, avatar from Google) with profiles (role)
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const admin = getSupabaseAdmin()
  if (!admin) {
    // Fallback to profiles-only if no service role key
    const { data: users, error } = await auth.db
      .from("profiles")
      .select("id, email, full_name, role, created_at")
      .order("created_at", { ascending: false })
    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
    return NextResponse.json({ users })
  }

  // 1. Fetch ALL auth users (has email, metadata with name/avatar)
  //    Paginate since listUsers returns max 1000 per page
  const allAuthUsers: Array<{
    id: string
    email?: string
    user_metadata?: Record<string, unknown>
    created_at: string
  }> = []

  let page = 1
  while (true) {
    const { data: { users: batch }, error } = await admin.auth.admin.listUsers({
      page,
      perPage: 1000,
    })
    if (error || !batch || batch.length === 0) break
    allAuthUsers.push(...batch)
    if (batch.length < 1000) break
    page++
  }

  // 2. Fetch all profiles (has role)
  const { data: profiles } = await admin
    .from("profiles")
    .select("id, email, full_name, role, created_at")

  const profileMap = new Map(
    (profiles || []).map((p: { id: string; email: string | null; full_name: string | null; role: string; created_at: string }) => [p.id, p])
  )

  // 3. Merge: auth user data takes priority for email/name, profile has role
  //    Also backfill profiles that are missing email/full_name
  const upsertBatch: Array<{ id: string; email: string; full_name: string }> = []

  const users = allAuthUsers.map((authUser) => {
    const profile = profileMap.get(authUser.id)
    const email = authUser.email || profile?.email || null
    const full_name =
      (authUser.user_metadata?.full_name as string) ||
      (authUser.user_metadata?.name as string) ||
      profile?.full_name ||
      null
    const role = profile?.role || "student"
    const created_at = profile?.created_at || authUser.created_at

    // Queue backfill if profile is missing or has empty email/name
    if (email && (!profile || !profile.email || !profile.full_name)) {
      upsertBatch.push({
        id: authUser.id,
        email: email,
        full_name: full_name || email.split("@")[0],
      })
    }

    return { id: authUser.id, email, full_name, role, created_at }
  })

  // 4. Backfill profiles in bulk (fire-and-forget, non-blocking)
  if (upsertBatch.length > 0) {
    admin
      .from("profiles")
      .upsert(
        upsertBatch.map((u) => ({
          id: u.id,
          email: u.email,
          full_name: u.full_name,
        })),
        { onConflict: "id", ignoreDuplicates: false }
      )
      .then(({ error }) => {
        if (error) console.warn("[admin/users] backfill error:", error.message)
      })
  }

  // Sort by created_at descending
  users.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  return NextResponse.json({ users })
}

// PATCH /api/admin/users - Update a user's role by email (admin only)
export async function PATCH(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const admin = getSupabaseAdmin()
  const db = admin || auth.db

  const body = await req.json()
  const { email, role } = body

  if (!email || !role || !["student", "teacher", "admin"].includes(role)) {
    return NextResponse.json({ error: "Valid email and role (student/teacher/admin) required" }, { status: 400 })
  }

  // First try profiles table
  const { data: targetUser } = await db
    .from("profiles")
    .select("id, email, role")
    .eq("email", email)
    .single()

  if (targetUser) {
    // User found in profiles — update role
    const { error: updateError } = await db
      .from("profiles")
      .update({ role })
      .eq("id", targetUser.id)

    if (updateError) {
      return NextResponse.json({ error: updateError.message }, { status: 500 })
    }
    return NextResponse.json({ success: true, user: { ...targetUser, role } })
  }

  // Not in profiles — search auth.users by email (needs admin client)
  if (!admin) {
    return NextResponse.json({ error: "User not found with that email" }, { status: 404 })
  }

  // Search auth users for the email
  const { data: { users: authUsers } } = await admin.auth.admin.listUsers()
  const authUser = authUsers?.find(
    (u) => u.email?.toLowerCase() === email.toLowerCase()
  )

  if (!authUser) {
    return NextResponse.json({ error: "User not found with that email" }, { status: 404 })
  }

  // Create profile and set role
  const fullName =
    (authUser.user_metadata?.full_name as string) ||
    (authUser.user_metadata?.name as string) ||
    email.split("@")[0]

  const { error: upsertError } = await admin
    .from("profiles")
    .upsert({
      id: authUser.id,
      email: authUser.email,
      full_name: fullName,
      role,
    }, { onConflict: "id" })

  if (upsertError) {
    return NextResponse.json({ error: upsertError.message }, { status: 500 })
  }

  return NextResponse.json({
    success: true,
    user: { id: authUser.id, email: authUser.email, role },
  })
}
