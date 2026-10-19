import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { logAdminAction } from "@/lib/auditLog"
import { adminPaymentDecisionSchema } from "@/lib/store/schemas"
import { issueDownloadsForOrder } from "@/lib/store/orders"

/**
 * POST /api/admin/store/payment — verify or reject a manual bKash/Nagad claim.
 *
 * This is the moment money becomes real: verifying releases the digital files
 * and moves the order to confirmed. The transition itself is one guarded SQL
 * statement, so double-clicking Verify performs the action once — it does not
 * confirm twice, re-issue downloads or write a second audit event.
 */
export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Unavailable" }, { status: 503 })

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 })
  }

  const parsed = adminPaymentDecisionSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.issues[0]?.message ?? "Invalid input." }, { status: 400 })
  }
  const { orderId, decision, reason } = parsed.data

  if (decision === "reject" && !reason) {
    return NextResponse.json(
      { error: "Give a reason — the buyer sees it and needs to know what to fix." },
      { status: 400 }
    )
  }

  const fn = decision === "verify" ? "store_verify_payment" : "store_reject_payment"
  const { data, error } = await db.rpc(fn, {
    p_order: orderId,
    p_admin: auth.user.id,
    p_admin_email: auth.user.email ?? null,
    [decision === "verify" ? "p_note" : "p_reason"]: reason ?? null,
  })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  const result = data as { changed?: boolean; payment_status?: string } | null

  // Issue digital entitlements only on the transition that actually happened.
  let issued = 0
  if (decision === "verify" && result?.changed) {
    issued = (await issueDownloadsForOrder(orderId)).length
  }

  await logAdminAction({
    admin_email: auth.user.email,
    action: decision === "verify" ? "store_verify_payment" : "store_reject_payment",
    entity_type: "store_order",
    entity_id: orderId,
    details: { changed: result?.changed ?? false, reason: reason ?? null, downloads_issued: issued },
  })

  return NextResponse.json({
    ok: true,
    changed: result?.changed ?? false,
    paymentStatus: result?.payment_status ?? null,
    downloadsIssued: issued,
    message: result?.changed
      ? (decision === "verify" ? "Payment verified." : "Payment rejected — the buyer can submit a corrected Transaction ID.")
      : "No change — this order was already handled.",
  })
}
