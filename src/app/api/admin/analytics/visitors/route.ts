import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * GET /api/admin/analytics/visitors?section=overview&days=30
 *
 * One database function per dashboard section (migrations 36 and 37). All
 * counting happens in Postgres: PostgREST caps selects at 1000 rows and
 * aggregates are disabled, so counting rows here would silently undercount.
 */
export const dynamic = "force-dynamic"

const ALLOWED_DAYS = new Set([7, 30, 90])
const RETENTION_WEEKS = 8
const TIMEZONE = "Asia/Dhaka"

type Section = "overview" | "realtime" | "behavior" | "acquisition" | "funnels" | "retention" | "patterns"

const SECTIONS: Record<Section, { fn: string; migration: number; args: (days: number) => Record<string, unknown> }> = {
  overview:    { fn: "admin_site_analytics", migration: 36, args: days => ({ p_days: days, p_tz: TIMEZONE }) },
  realtime:    { fn: "admin_realtime",       migration: 37, args: () => ({}) },
  behavior:    { fn: "admin_behavior",       migration: 37, args: days => ({ p_days: days, p_tz: TIMEZONE }) },
  acquisition: { fn: "admin_acquisition",    migration: 37, args: days => ({ p_days: days, p_tz: TIMEZONE }) },
  funnels:     { fn: "admin_funnels",        migration: 37, args: days => ({ p_days: days, p_tz: TIMEZONE }) },
  retention:   { fn: "admin_retention",      migration: 37, args: () => ({ p_weeks: RETENTION_WEEKS, p_tz: TIMEZONE }) },
  patterns:    { fn: "admin_patterns",       migration: 37, args: days => ({ p_days: days, p_tz: TIMEZONE }) },
}

const MIGRATION_FILES: Record<number, string> = {
  36: "supabase/migrations/36_site_visits.sql",
  37: "supabase/migrations/37_site_behavior.sql",
}

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const params = req.nextUrl.searchParams
  const sectionName = params.get("section") ?? "overview"
  // Own keys only, so "__proto__" and friends are not sections.
  if (!Object.hasOwn(SECTIONS, sectionName)) {
    return NextResponse.json({ error: "Unknown analytics section." }, { status: 400 })
  }
  const section = SECTIONS[sectionName as Section]

  const requested = Number(params.get("days"))
  const days = ALLOWED_DAYS.has(requested) ? requested : 30

  const db = getSupabaseAdmin()
  if (!db) {
    console.error("[admin/visitors] Supabase admin client is not configured")
    return NextResponse.json({ error: "Analytics are unavailable right now." }, { status: 500 })
  }

  const { data, error } = await db.rpc(section.fn, section.args(days))
  if (error) {
    console.error(`[admin/visitors] ${section.fn} failed (${error.code ?? "no code"}): ${error.message}`)
    // PGRST202 / 42883 = function not found: the migration has not been run yet.
    const notSetUp = error.code === "PGRST202" || error.code === "42883"
    return NextResponse.json(
      {
        error: notSetUp
          ? `This section is not set up yet: run ${MIGRATION_FILES[section.migration]} in the Supabase SQL editor.`
          : "Could not load visitor analytics.",
        notSetUp,
      },
      { status: notSetUp ? 503 : 500 }
    )
  }
  return NextResponse.json(data)
}
