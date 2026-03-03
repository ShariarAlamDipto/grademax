import { NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"

/**
 * POST /api/admin/bootstrap
 * Auto-promotes the super admin email to admin role.
 * Called on login to ensure the admin always has access.
 */
export async function POST() {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (!isSuperAdmin(user.email)) {
    return NextResponse.json({ error: "Not a super admin" }, { status: 403 })
  }

  // Use service role to bypass RLS, fall back to regular client
  const admin = getSupabaseAdmin()
  const db = admin || supabase

  // Ensure profile exists before updating role
  await db
    .from("profiles")
    .upsert(
      { id: user.id, email: user.email },
      { onConflict: "id", ignoreDuplicates: true }
    )

  const { error } = await db
    .from("profiles")
    .update({ role: "admin" })
    .eq("id", user.id)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true, role: "admin" })
}
