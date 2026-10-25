import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { REPORT_TZ, parseAnalyticsQuery, type AnalyticsRange } from "@/lib/analyticsQuery"

/**
 * GET /api/admin/analytics/visitors?section=overview&range=30&country=BD
 *
 * One database function per dashboard section (migrations 36, 37 and 38). All
 * counting happens in Postgres: PostgREST caps selects at 1000 rows and
 * aggregates are disabled, so counting rows here would silently undercount.
 * See analyticsQuery.ts for range and country.
 */
export const dynamic = "force-dynamic"

const RETENTION_WEEKS = 8

type Section = "overview" | "countries" | "realtime" | "behavior" | "acquisition" | "funnels" | "retention" | "patterns" | "tools" | "performance"
type Args = Record<string, unknown>

/** Only send optional parameters when they are used, so the 36/37 functions still answer the default view. */
function rangeArgs(range: AnalyticsRange): Args {
  return "days" in range ? { p_days: range.days, p_tz: REPORT_TZ } : { p_from: range.from, p_to: range.to, p_tz: REPORT_TZ }
}
const countryArg = (country: string | null): Args => (country ? { p_country: country } : {})

const SECTIONS: Record<Section, { fn: string; args: (range: AnalyticsRange, country: string | null) => Args }> = {
  overview:    { fn: "admin_site_analytics", args: (r, c) => ({ ...rangeArgs(r), ...countryArg(c) }) },
  countries:   { fn: "admin_countries",      args: r => rangeArgs(r) },
  realtime:    { fn: "admin_realtime",       args: (_r, c) => countryArg(c) },
  behavior:    { fn: "admin_behavior",       args: (r, c) => ({ ...rangeArgs(r), ...countryArg(c) }) },
  acquisition: { fn: "admin_acquisition",    args: (r, c) => ({ ...rangeArgs(r), ...countryArg(c) }) },
  funnels:     { fn: "admin_funnels",        args: (r, c) => ({ ...rangeArgs(r), ...countryArg(c) }) },
  retention:   { fn: "admin_retention",      args: (_r, c) => ({ p_weeks: RETENTION_WEEKS, p_tz: REPORT_TZ, ...countryArg(c) }) },
  patterns:    { fn: "admin_patterns",       args: (r, c) => ({ ...rangeArgs(r), ...countryArg(c) }) },
  // Always sends p_country so only the migration-38 function can answer.
  tools:       { fn: "admin_tools",          args: (r, c) => ({ ...rangeArgs(r), p_country: c }) },
  performance: { fn: "admin_performance",    args: (r, c) => ({ ...rangeArgs(r), p_country: c }) },
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

  const query = parseAnalyticsQuery(params)
  if (!query.ok) return NextResponse.json({ error: query.error }, { status: 400 })

  const db = getSupabaseAdmin()
  if (!db) {
    console.error("[admin/visitors] Supabase admin client is not configured")
    return NextResponse.json({ error: "Analytics are unavailable right now." }, { status: 500 })
  }

  const { data, error } = await db.rpc(section.fn, section.args(query.range, query.country))
  if (error) {
    console.error(`[admin/visitors] ${section.fn} failed (${error.code ?? "no code"}): ${error.message}`)
    // PGRST202 / 42883 = no function with these parameters: a migration is missing.
    const notSetUp = error.code === "PGRST202" || error.code === "42883"
    return NextResponse.json(
      {
        error: notSetUp
          ? "This view needs the latest analytics migrations: run supabase/migrations/37_site_behavior.sql, 38_site_analytics_controls.sql and 40_site_performance_alerts.sql (in that order) in the Supabase SQL editor."
          : "Could not load visitor analytics.",
        notSetUp,
      },
      { status: notSetUp ? 503 : 500 }
    )
  }
  return NextResponse.json(data)
}
