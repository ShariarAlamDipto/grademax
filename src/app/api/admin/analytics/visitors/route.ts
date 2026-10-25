import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * GET /api/admin/analytics/visitors?days=30 — the Visitors dashboard data.
 *
 * All counting happens in admin_site_analytics() (migration 36): PostgREST caps
 * selects at 1000 rows and aggregates are disabled, so counting rows here would
 * silently undercount.
 */
export const dynamic = "force-dynamic"

const ALLOWED_DAYS = new Set([7, 30, 90])
const TIMEZONE = "Asia/Dhaka"

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const requested = Number(req.nextUrl.searchParams.get("days"))
  const days = ALLOWED_DAYS.has(requested) ? requested : 30

  const db = getSupabaseAdmin()
  if (!db) {
    console.error("[admin/visitors] Supabase admin client is not configured")
    return NextResponse.json({ error: "Analytics are unavailable right now." }, { status: 500 })
  }

  const { data, error } = await db.rpc("admin_site_analytics", { p_days: days, p_tz: TIMEZONE })
  if (error) {
    console.error(`[admin/visitors] rpc failed (${error.code ?? "no code"}): ${error.message}`)
    // PGRST202 = function not found: migration 36 has not been applied yet.
    const notSetUp = error.code === "PGRST202" || error.code === "42883"
    return NextResponse.json(
      {
        error: notSetUp
          ? "Visitor tracking is not set up yet: run supabase/migrations/36_site_visits.sql in the Supabase SQL editor."
          : "Could not load visitor analytics.",
        notSetUp,
      },
      { status: notSetUp ? 503 : 500 }
    )
  }
  return NextResponse.json(data)
}
