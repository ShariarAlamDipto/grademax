/**
 * Order lifecycle: creation, payment claims, verification, digital entitlement.
 *
 * The transactional work lives in Postgres functions (migration 23). This file
 * is the typed seam over them: it maps their ERRCODEs to messages a buyer can
 * act on, and it owns the one thing SQL cannot do — generating a download token
 * whose plaintext is never stored.
 */
import { notifyNewOrder } from "./notify"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { generateOrderNumber } from "./tokens"
import type { CheckoutInput } from "./schemas"
import type { OrderStatus, PaymentMethod, PaymentStatus, VariantKind } from "./types"

/** How long a digital download link stays usable after payment is verified. */
const DOWNLOAD_VALID_DAYS = 365

/**
 * Postgres ERRCODEs raised by `store_create_order`, mapped to buyer-facing
 * copy. The database is the single place these rules are enforced; this just
 * translates them.
 */
const ORDER_ERRORS: Record<string, string> = {
  P0001: "Something in your cart is not valid. Please refresh and try again.",
  P0002: "An item in your cart no longer exists. Please refresh and try again.",
  P0003: "One of the items in your cart is no longer on sale.",
  P0004: "That title has just sold out. Please adjust your cart and try again.",
  P0005: "Cash on delivery cannot be used for a digital download — there is nothing to deliver. Please pay with bKash or Nagad.",
  P0006: "Please choose a district and enter your full delivery address.",
  P0007: "You can order at most 10 copies of one title.",
  P0008: "Please sign in to place your order.",
  P0009: "An email address is required so we can send your receipt.",
  P0010: "PDF downloads are not on sale at the moment. Please order the printed copy instead.",
}

/**
 * Build the one printable line a courier reads off the parcel.
 *
 * The parts are stored separately too, but a delivery label needs a single
 * string, and composing it here means every order is formatted identically
 * rather than however each buyer chose to type it.
 */
export function composeAddressLine(d: {
  houseNo: string
  roadNo: string | null
  area: string
  city: string
  landmark: string | null
  addressLine: string | null
  postcode: string | null
}): string {
  const parts = [
    `House ${d.houseNo}`,
    d.roadNo ? `Road ${d.roadNo}` : null,
    d.area,
    d.city,
    d.postcode ? `Postcode ${d.postcode}` : null,
    d.landmark ? `Near ${d.landmark}` : null,
    d.addressLine,
  ]
  return parts.filter(Boolean).join(", ")
}

export interface CreatedOrder {
  orderId: string
  orderNumber: string
  subtotalBdt: number
  deliveryBdt: number
  totalBdt: number
  hasPrint: boolean
  hasDigital: boolean
  paymentStatus: PaymentStatus
}

export type CreateOrderResult =
  | { ok: true; order: CreatedOrder }
  | { ok: false; message: string; code?: string }

export async function createOrder(
  input: CheckoutInput,
  userId: string | null
): Promise<CreateOrderResult> {
  const db = getSupabaseAdmin()
  if (!db) return { ok: false, message: "The store is temporarily unavailable." }

  const orderNumber = await generateOrderNumber()

  const { data, error } = await db.rpc("store_create_order", {
    p_order_number: orderNumber,
    p_user_id: userId,
    p_name: input.customer.name,
    p_phone: input.customer.phone,
    p_email: input.customer.email,
    p_district_id: input.delivery?.districtId ?? null,
    p_city: input.delivery?.city ?? null,
    p_area: input.delivery?.area ?? null,
    p_address: input.delivery ? composeAddressLine(input.delivery) : null,
    p_postcode: input.delivery?.postcode ?? null,
    p_notes: input.notes,
    p_payment_method: input.paymentMethod,
    p_source_path: input.source?.path ?? null,
    p_source_referrer: input.source?.referrer ?? null,
    p_items: input.items.map(i => ({ variant_id: i.variantId, quantity: i.quantity })),
    p_house_no: input.delivery?.houseNo ?? null,
    p_road_no: input.delivery?.roadNo ?? null,
    p_landmark: input.delivery?.landmark ?? null,
    p_alt_phone: input.customer.altPhone ?? null,
  })

  if (error) {
    const code = (error as { code?: string }).code ?? ""
    return {
      ok: false,
      code,
      message: ORDER_ERRORS[code] ?? "We could not place your order. Please try again.",
    }
  }

  const r = data as Record<string, unknown>
  const orderId = String(r.order_id)

  // Tell the shopkeeper. Deliberately awaited rather than left dangling: on a
  // serverless host the function can be frozen the moment this handler returns,
  // which would drop a detached request. It is bounded by its own timeout and
  // never throws, so the order is safe either way.
  await notifyOrderPlaced(orderId)

  return {
    ok: true,
    order: {
      orderId,
      orderNumber: String(r.order_number),
      subtotalBdt: Number(r.subtotal_bdt),
      deliveryBdt: Number(r.delivery_bdt),
      totalBdt: Number(r.total_bdt),
      hasPrint: Boolean(r.has_print),
      hasDigital: Boolean(r.has_digital),
      paymentStatus: String(r.payment_status) as PaymentStatus,
    },
  }
}

// ── Payment claims ───────────────────────────────────────────────────────────

export type SubmitPaymentResult =
  | { ok: true }
  /**
   * `duplicate` is reported to the buyer in exactly the same words as success.
   * Telling them a Transaction ID is already in use would confirm that a given
   * ID exists, and would let someone burn a stranger's receipt by claiming it
   * first. The collision is flagged for the admin instead.
   */
  | { ok: false; reason: "not_found" | "wrong_state" | "duplicate" | "error"; message: string }

/**
 * Push a new order to the shopkeeper's phone. Never throws, for the same reason
 * `recordOrderEvent` does not: the buyer's order has already been written, and
 * a notification problem must not be reported to them as a failed checkout.
 */
async function notifyOrderPlaced(orderId: string): Promise<void> {
  try {
    const view = await getOrderById(orderId)
    if (view) await notifyNewOrder(view)
  } catch {
    // Non-fatal by design.
  }
}

/**
 * Append a line to an order's history. Never throws: it is a diagnostic trail,
 * and failing to write one must not take down the flow it is describing.
 */
async function recordOrderEvent(orderId: string, field: string, note: string): Promise<void> {
  try {
    const db = getSupabaseAdmin()
    if (!db) return
    await db.from("store_order_events").insert({ order_id: orderId, field, note })
  } catch {
    // Non-fatal by design.
  }
}

export async function submitPayment(args: {
  orderId: string
  method: Exclude<PaymentMethod, "cod">
  senderMsisdn: string
  transactionId: string
  amountBdt?: number
}): Promise<SubmitPaymentResult> {
  const db = getSupabaseAdmin()
  if (!db) return { ok: false, reason: "error", message: "The store is temporarily unavailable." }

  const { error: insertError } = await db.from("store_payments").insert({
    order_id: args.orderId,
    method: args.method,
    sender_msisdn: args.senderMsisdn,
    transaction_id: args.transactionId,
    amount_bdt: args.amountBdt ?? null,
  })

  if (insertError) {
    const code = (insertError as { code?: string }).code

    // 23505 = unique violation, from either partial index: this Transaction ID
    // is already claimed, or this order already has a live claim. The buyer is
    // told nothing (see the route), but the owner must be able to see it —
    // otherwise a buyer whose receipt was claimed by someone else has no
    // explanation and no trail.
    if (code === "23505") {
      await recordOrderEvent(args.orderId, "payment_conflict",
        `${args.method} · ${args.transactionId} · already claimed, or this order already has a live claim`)
      return { ok: false, reason: "duplicate", message: "Payment recorded." }
    }

    // A genuine failure. The buyer-facing wording stays uniform so it cannot be
    // used to probe the system, but this must NOT vanish: if inserts started
    // failing, every buyer would be told their payment was recorded while
    // nothing was written, and nobody would find out until someone complained.
    await recordOrderEvent(args.orderId, "payment_error",
      `Could not record a ${args.method} payment (${code ?? "unknown"}). The buyer was told it succeeded.`)
    return { ok: false, reason: "error", message: "We could not record your payment. Please try again." }
  }

  // Only move the order once the claim exists, and only from the state that
  // expects one — so a replayed request cannot walk a verified order backwards.
  const { data, error } = await db
    .from("store_orders")
    .update({ payment_status: "submitted", updated_at: new Date().toISOString() })
    .eq("id", args.orderId)
    .eq("payment_status", "awaiting_payment")
    .select("id")

  if (error) return { ok: false, reason: "error", message: "We could not record your payment." }
  if (!data || data.length === 0) return { ok: false, reason: "wrong_state", message: "Payment recorded." }

  await db.from("store_order_events").insert({
    order_id: args.orderId,
    field: "payment_status",
    from_value: "awaiting_payment",
    to_value: "submitted",
    note: `${args.method} · ${args.transactionId}`,
  })

  return { ok: true }
}

// ── Digital entitlement ──────────────────────────────────────────────────────

export interface IssuedDownload {
  orderItemId: string
  productTitle: string
  entitlementId: string
}

/**
 * Create one download entitlement per digital line of a verified order.
 *
 * Safe to call repeatedly: `store_downloads` is UNIQUE on `order_item_id`, so a
 * second call inserts nothing. That property is what lets it run both from the
 * verify handler and as a lazy repair on the tracking page, if issuance ever
 * failed after the payment was verified.
 *
 * No secret is created here. Access is granted at read time by a short-lived
 * signed grant — see `downloadGrant.ts`.
 */
export async function issueDownloadsForOrder(orderId: string): Promise<IssuedDownload[]> {
  const db = getSupabaseAdmin()
  if (!db) return []

  const { data: order } = await db
    .from("store_orders")
    .select("id, payment_status")
    .eq("id", orderId)
    .maybeSingle()

  // Re-checked here rather than trusted from the caller: this function mints
  // access to paid files, so it verifies payment itself.
  if (!order || order.payment_status !== "verified") return []

  const { data: items } = await db
    .from("store_order_items")
    .select("id, product_title, variant_kind")
    .eq("order_id", orderId)
    .eq("variant_kind", "digital")

  if (!items?.length) return []

  const { data: existing } = await db
    .from("store_downloads")
    .select("order_item_id")
    .eq("order_id", orderId)
  const already = new Set((existing ?? []).map((d: { order_item_id: string }) => d.order_item_id))

  const issued: IssuedDownload[] = []
  const expiresAt = new Date(Date.now() + DOWNLOAD_VALID_DAYS * 86_400_000).toISOString()

  for (const item of items as { id: string; product_title: string }[]) {
    if (already.has(item.id)) continue
    const { data: created, error } = await db
      .from("store_downloads")
      .insert({ order_item_id: item.id, order_id: orderId, expires_at: expiresAt })
      .select("id")
      .single()
    if (!error && created) {
      issued.push({
        orderItemId: item.id,
        productTitle: item.product_title,
        entitlementId: created.id as string,
      })
    }
  }
  return issued
}

// ── Reading orders ───────────────────────────────────────────────────────────

export interface OrderView {
  id: string
  order_number: string
  customer_name: string
  customer_phone: string
  customer_email: string | null
  district_name: string | null
  city: string | null
  area: string | null
  address_line: string | null
  house_no: string | null
  road_no: string | null
  landmark: string | null
  alt_phone: string | null
  postcode: string | null
  has_print: boolean
  has_digital: boolean
  subtotal_bdt: number
  delivery_bdt: number
  discount_bdt: number
  total_bdt: number
  payment_method: PaymentMethod
  payment_status: PaymentStatus
  order_status: OrderStatus
  courier_name: string | null
  tracking_code: string | null
  created_at: string
  items: {
    id: string
    product_title: string
    variant_label: string
    variant_kind: VariantKind
    unit_price_bdt: number
    quantity: number
    line_total_bdt: number
  }[]
}

const ORDER_VIEW_COLUMNS =
  "id, order_number, customer_name, customer_phone, customer_email, city, area, address_line, " +
  "house_no, road_no, landmark, alt_phone, postcode, " +
  "has_print, has_digital, subtotal_bdt, delivery_bdt, discount_bdt, total_bdt, " +
  "payment_method, payment_status, order_status, courier_name, tracking_code, created_at, " +
  "store_districts(name), " +
  "store_order_items(id, product_title, variant_label, variant_kind, unit_price_bdt, quantity, line_total_bdt)"

interface RawOrder extends Omit<OrderView, "district_name" | "items"> {
  store_districts: { name: string } | null
  store_order_items: OrderView["items"]
}

function shapeOrder(raw: RawOrder): OrderView {
  const { store_districts, store_order_items, ...rest } = raw
  return { ...rest, district_name: store_districts?.name ?? null, items: store_order_items ?? [] }
}

export async function getOrderByNumber(orderNumber: string): Promise<OrderView | null> {
  const db = getSupabaseAdmin()
  if (!db) return null
  const { data, error } = await db
    .from("store_orders")
    .select(ORDER_VIEW_COLUMNS)
    .eq("order_number", orderNumber)
    .maybeSingle()
  if (error || !data) return null
  return shapeOrder(data as unknown as RawOrder)
}

export async function getOrderById(orderId: string): Promise<OrderView | null> {
  const db = getSupabaseAdmin()
  if (!db) return null
  const { data, error } = await db
    .from("store_orders")
    .select(ORDER_VIEW_COLUMNS)
    .eq("id", orderId)
    .maybeSingle()
  if (error || !data) return null
  return shapeOrder(data as unknown as RawOrder)
}
