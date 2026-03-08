import { NextResponse } from "next/server"
import { requireAuth } from "@/lib/apiAuth"

/**
 * GET /api/auth/me
 * Returns the current user's profile using server-side auth.
 * Used as a fallback when client-side Supabase query fails (e.g. RLS issues).
 */
export async function GET() {
  const auth = await requireAuth()
  if ("error" in auth) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { user, db } = auth

  const { data: profile, error } = await db
    .from("profiles")
    .select("id, email, full_name, avatar_url, study_level, marks_goal_pct, role")
    .eq("id", user.id)
    .single()

  if (error || !profile) {
    // Profile doesn't exist — return minimal info from auth user
    return NextResponse.json({
      id: user.id,
      email: user.email || null,
      full_name:
        (user.user_metadata?.full_name as string) ||
        (user.user_metadata?.name as string) ||
        null,
      avatar_url: (user.user_metadata?.avatar_url as string) || null,
      study_level: null,
      marks_goal_pct: 90,
      role: "student",
    })
  }

  return NextResponse.json(profile)
}
