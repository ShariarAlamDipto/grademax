import { NextRequest, NextResponse } from "next/server"
import { getOrderByNumber, issueDownloadsForOrder } from "@/lib/store/orders"
import { orderLookupSchema } from "@/lib/store/schemas"
import { checkRateLimitByIp } from "@/lib/store/rateLimit"
import { phoneMatches } from "@/lib/store/phone"
import { maskPhone } from "@/lib/store/format"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getSettings } from "@/lib/store/settings"
import { mintDownloadGrant } from "@/lib/store/downloadGrant"

/**
 * POST /api/store/orders/lookup — guest order tracking.
 *
 * Order number plus phone number is not high entropy on its own, so this is
 * rate limited hard and returns a masked view: enough for the buyer to confirm
 * it is their order, not enough to harvest addresses if someone did guess.
 */
export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  if (!(await checkRateLimitByIp("orderLookup"))) {
    return NextResponse.json(
      { error: "Too many lookups. Please wait a few minutes and try again." },
      { status: 429 }
    )
  }

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 })
  }

  const parsed = orderLookupSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: "Enter your order number and the phone number you ordered with." }, { status: 400 })
  }

  const order = await getOrderByNumber(parsed.data.orderNumber)
  if (!order || !phoneMatches(order.customer_phone, parsed.data.phone)) {
    return NextResponse.json(
      { error: "We could not find an order with that number and phone number." },
      { status: 404 }
    )
  }

  // Lazy repair: if the order was verified but token issuance failed at the
  // time, mint the tokens now rather than leaving a paid buyer stranded.
  let downloads: { productTitle: string; url: string; remaining: number }[] = []
  if (order.payment_status === "verified" && order.has_digital) {
    await issueDownloadsForOrder(order.id)
    downloads = await listDownloadLinks(order.id)
  }

  const settings = await getSettings()

  return NextResponse.json({
    order: {
      orderNumber: order.order_number,
      placedAt: order.created_at,
      customerName: order.customer_name,
      phone: maskPhone(order.customer_phone),
      district: order.district_name,
      // The full street address is deliberately not returned.
      subtotalBdt: order.subtotal_bdt,
      deliveryBdt: order.delivery_bdt,
      totalBdt: order.total_bdt,
      paymentMethod: order.payment_method,
      paymentStatus: order.payment_status,
      orderStatus: order.order_status,
      courierName: order.courier_name,
      trackingCode: order.tracking_code,
      hasPrint: order.has_print,
      hasDigital: order.has_digital,
      items: order.items.map(i => ({
        title: i.product_title,
        variant: i.variant_label,
        kind: i.variant_kind,
        quantity: i.quantity,
        lineTotalBdt: i.line_total_bdt,
      })),
      downloads,
    },
    payTo: order.payment_method === "bkash" ? settings.bkashNumber
         : order.payment_method === "nagad" ? settings.nagadNumber
         : null,
    slaHours: settings.verificationSlaHours,
  })
}

/**
 * Mint a fresh thirty-minute grant per entitlement.
 *
 * The buyer never holds a permanent download credential: proving the order is
 * theirs is what produces a link, and the link goes stale on its own. The
 * entitlement id alone is useless without a valid signature.
 */
async function listDownloadLinks(orderId: string) {
  const db = getSupabaseAdmin()
  if (!db) return []
  const { data } = await db
    .from("store_downloads")
    .select("id, revoked_at, download_count, max_downloads, store_order_items(product_title)")
    .eq("order_id", orderId)
  if (!data) return []
  return (data as unknown as {
    id: string
    revoked_at: string | null
    download_count: number
    max_downloads: number
    store_order_items: { product_title: string } | null
  }[])
    .filter(d => !d.revoked_at && d.download_count < d.max_downloads)
    .map(d => ({
      productTitle: d.store_order_items?.product_title ?? "Your download",
      url: `/api/store/download/${mintDownloadGrant(d.id)}`,
      remaining: d.max_downloads - d.download_count,
    }))
}
