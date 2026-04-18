import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * GET /api/admin/check-role?email=user@example.com
 * Diagnostic endpoint: check a user's actual role in the database.
 * Admin-only.
 */
export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const email = req.nextUrl.searchParams.get("email")
  if (!email) {
    return NextResponse.json({ error: "email query param required" }, { status: 400 })
  }

  const admin = getSupabaseAdmin()
  const db = admin || auth.db

  // 1. Check profiles table (case-insensitive)
  const { data: profile, error: profileErr } = await db
    .from("profiles")
    .select("id, email, full_name, role, created_at, updated_at")
    .ilike("email", email.trim())
    .single()

  // 2. Check auth.users if admin client available (paginated to avoid loading all users at once)
  let authUser = null
  if (admin) {
    const normalizedEmail = email.toLowerCase().trim()
    let page = 1
    while (!authUser) {
      const { data: { users: batch }, error: listErr } = await admin.auth.admin.listUsers({ page, perPage: 1000 })
      if (listErr || !batch || batch.length === 0) break
      authUser = batch.find((u) => u.email?.toLowerCase() === normalizedEmail) || null
      if (batch.length < 1000) break
      page++
    }
  }

  return NextResponse.json({
    email: email.trim(),
    profileFound: !!profile,
    profileError: profileErr?.message || null,
    profile: profile
      ? {
          id: profile.id,
          email: profile.email,
          full_name: profile.full_name,
          role: profile.role,
          created_at: profile.created_at,
          updated_at: profile.updated_at,
        }
      : null,
    authUserFound: !!authUser,
    authUserEmail: authUser?.email || null,
    authUserId: authUser?.id || null,
    roleColumnExists: profileErr?.message?.includes("column") ? false : true,
    diagnosis: !profile && !authUser
      ? "User not found in profiles or auth.users. They may not have signed up yet."
      : !profile && authUser
        ? "User exists in auth but has no profile row. The handle_new_user trigger may not have fired."
        : profile && !profile.role
          ? "Profile exists but role column is NULL. The role column may not have been added to the table."
          : profile?.role === "student"
            ? "Profile exists with role='student'. The admin update may not have been applied, or a subsequent operation reset it."
            : profile
              ? `Profile exists with role='${profile.role}'. Role is correctly set — the issue may be client-side caching. Ask the user to hard-refresh (Ctrl+Shift+R).`
              : "Unknown state",
  })
}
