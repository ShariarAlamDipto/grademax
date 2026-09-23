import { NextResponse } from "next/server"
import { requireAuth } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * GET /api/store/orders/mine — the signed-in buyer's own orders.
 *
 * Needed because ordering now requires an account: without this, someone who
 * lost their order number would have no way back to their order at all. Scoped
 * hard to `user_id`, so it can only ever return the caller's own rows.
 */
export const dynamic = "force-dynamic"

export async function GET() {
  const auth = await requireAuth()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ orders: [] })

  const { data, error } = await db
    .from("store_orders")
    .select("order_number, created_at, total_bdt, payment_status, order_status, has_print, has_digital, store_order_items(product_title, quantity)")
    .eq("user_id", auth.user.id)
    .order("created_at", { ascending: false })
    .limit(30)

  if (error) return NextResponse.json({ orders: [] })

  const orders = (data ?? []).map((o: Record<string, unknown>) => ({
    orderNumber: o.order_number,
    placedAt: o.created_at,
    totalBdt: o.total_bdt,
    paymentStatus: o.payment_status,
    orderStatus: o.order_status,
    titles: ((o.store_order_items ?? []) as { product_title: string; quantity: number }[])
      .map(i => `${i.product_title}${i.quantity > 1 ? ` × ${i.quantity}` : ""}`),
  }))

  return NextResponse.json({ orders })
}
