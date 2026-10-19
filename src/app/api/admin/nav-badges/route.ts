import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * GET /api/admin/nav-badges
 * Returns lightweight counts for nav badge indicators.
 */
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  const [missingQPRes, missingMSRes] = await Promise.all([
    db.from("papers").select("id", { count: "exact", head: true }).is("pdf_url", null),
    db.from("papers").select("id", { count: "exact", head: true }).is("markscheme_pdf_url", null),
  ])

  const missingPapers = (missingQPRes.count ?? 0) + (missingMSRes.count ?? 0)

  // Count question pages with no topic classification yet
  let unreviewedQuestions = 0
  try {
    const { count } = await db
      .from("pages")
      .select("id", { count: "exact", head: true })
      .eq("is_question", true)
      .or("topics.is.null,topics.eq.{}")
    unreviewedQuestions = count ?? 0
  } catch {
    // Non-fatal — badge simply shows 0
  }

  // Payments claimed but not yet checked. This is the one badge here that is
  // time-sensitive: until it clears, a buyer has paid and received nothing.
  let pendingOrders = 0
  try {
    const { count } = await db
      .from("store_orders")
      .select("id", { count: "exact", head: true })
      .eq("payment_status", "submitted")
      .neq("order_status", "cancelled")
    pendingOrders = count ?? 0
  } catch {
    // Non-fatal — the store may not be migrated in this environment yet.
  }

  return NextResponse.json({ missingPapers, unreviewedQuestions, pendingOrders })
}
