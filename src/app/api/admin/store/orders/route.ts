import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { logAdminAction } from "@/lib/auditLog"
import { adminOrderUpdateSchema } from "@/lib/store/schemas"

/**
 * Admin order list and status updates.
 *
 * The list is filterable by payment state, fulfilment state and district —
 * district being the one the owner asked for, to see where orders come from.
 */
export const dynamic = "force-dynamic"

const LIST_COLUMNS =
  "id, order_number, customer_name, customer_phone, customer_email, city, area, address_line, " +
  "has_print, has_digital, subtotal_bdt, delivery_bdt, total_bdt, payment_method, payment_status, " +
  "order_status, courier_name, tracking_code, source_path, source_referrer, admin_note, created_at, " +
  "store_districts(id, name, division, is_metro), " +
  "store_order_items(id, product_title, variant_label, variant_kind, quantity, unit_price_bdt, line_total_bdt), " +
  "store_payments(id, method, sender_msisdn, transaction_id, amount_bdt, status, rejection_reason, created_at)"

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Unavailable" }, { status: 503 })

  const url = new URL(req.url)
  const paymentStatus = url.searchParams.get("payment_status")
  const orderStatus = url.searchParams.get("order_status")
  const districtId = url.searchParams.get("district_id")
  const search = url.searchParams.get("q")?.trim()
  const limit = Math.min(Number(url.searchParams.get("limit")) || 50, 200)
  const offset = Math.max(Number(url.searchParams.get("offset")) || 0, 0)

  let query = db
    .from("store_orders")
    .select(LIST_COLUMNS, { count: "exact" })
    .order("created_at", { ascending: false })
    .range(offset, offset + limit - 1)

  if (paymentStatus) query = query.eq("payment_status", paymentStatus)
  if (orderStatus) query = query.eq("order_status", orderStatus)
  if (districtId) query = query.eq("district_id", Number(districtId))
  if (search) {
    // Escape PostgREST's or() delimiters so a search string cannot alter the filter.
    const safe = search.replace(/[(),*]/g, "")
    if (safe) query = query.or(`order_number.ilike.*${safe}*,customer_name.ilike.*${safe}*,customer_phone.ilike.*${safe}*`)
  }

  const { data, error, count } = await query
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ orders: data ?? [], total: count ?? 0, limit, offset })
}

export async function PATCH(req: NextRequest) {
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

  const parsed = adminOrderUpdateSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.issues[0]?.message ?? "Invalid input." }, { status: 400 })
  }
  const { orderId, orderStatus, courierName, trackingCode, adminNote } = parsed.data

  const { data: before } = await db
    .from("store_orders")
    .select("order_status, order_number")
    .eq("id", orderId)
    .maybeSingle()
  if (!before) return NextResponse.json({ error: "Order not found." }, { status: 404 })

  // Cancelling has to give the stock back, which the SQL function does
  // atomically and exactly once. Never do it with a plain UPDATE here.
  if (orderStatus === "cancelled") {
    const { data } = await db.rpc("store_cancel_order", {
      p_order: orderId,
      p_admin: auth.user.id,
      p_admin_email: auth.user.email ?? null,
      p_reason: adminNote ?? "Cancelled by admin",
    })
    await logAdminAction({
      admin_email: auth.user.email,
      action: "store_cancel_order",
      entity_type: "store_order",
      entity_id: orderId,
      details: { order_number: before.order_number, result: data },
    })
    return NextResponse.json({ ok: true, cancelled: true })
  }

  const patch: Record<string, unknown> = { updated_at: new Date().toISOString() }
  if (orderStatus !== undefined) patch.order_status = orderStatus
  if (courierName !== undefined) patch.courier_name = courierName
  if (trackingCode !== undefined) patch.tracking_code = trackingCode
  if (adminNote !== undefined) patch.admin_note = adminNote

  const { error } = await db.from("store_orders").update(patch).eq("id", orderId)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  if (orderStatus && orderStatus !== before.order_status) {
    await db.from("store_order_events").insert({
      order_id: orderId,
      field: "order_status",
      from_value: before.order_status,
      to_value: orderStatus,
      actor_id: auth.user.id,
      actor_email: auth.user.email ?? null,
      note: adminNote ?? null,
    })
  }

  await logAdminAction({
    admin_email: auth.user.email,
    action: "store_update_order",
    entity_type: "store_order",
    entity_id: orderId,
    details: { order_number: before.order_number, from: before.order_status, to: orderStatus ?? null },
  })

  return NextResponse.json({ ok: true })
}
