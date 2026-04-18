import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * GET /api/admin/audit-log?limit=50&offset=0&action=&entity_type=
 * Returns paginated audit log entries.
 */
export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const limit = Math.min(parseInt(req.nextUrl.searchParams.get("limit") || "50"), 200)
  const offset = parseInt(req.nextUrl.searchParams.get("offset") || "0")
  const action = req.nextUrl.searchParams.get("action") || ""
  const entityType = req.nextUrl.searchParams.get("entity_type") || ""

  try {
    let query = db
      .from("admin_audit_log")
      .select("id, created_at, admin_email, action, entity_type, entity_id, details", { count: "exact" })
      .order("created_at", { ascending: false })
      .range(offset, offset + limit - 1)

    if (action) query = query.eq("action", action)
    if (entityType) query = query.eq("entity_type", entityType)

    const { data, error, count } = await query
    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
    return NextResponse.json({ entries: data || [], total: count ?? 0 })
  } catch {
    // Table doesn't exist yet
    return NextResponse.json({ entries: [], total: 0, note: "Audit log table not yet created" })
  }
}
