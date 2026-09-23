import { NextRequest, NextResponse } from "next/server"
import { priceCart } from "@/lib/store/pricing"
import { cartSchema } from "@/lib/store/schemas"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * POST /api/store/cart — price a cart.
 *
 * The cart itself lives in the buyer's browser, but the totals shown to them
 * must come from here, so the figure on the cart page is the same figure the
 * order is written with. The request carries variant IDs and quantities only;
 * a price sent by the client is not read.
 */
export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 })
  }

  const parsed = cartSchema.safeParse((body as { items?: unknown })?.items)
  if (!parsed.success) {
    return NextResponse.json({ error: "Your cart could not be read.", lines: [] }, { status: 400 })
  }

  // The district is optional: on the cart page nothing has been chosen yet, so
  // delivery shows as "calculated at checkout" rather than a guess.
  const districtId = Number((body as { districtId?: unknown })?.districtId)
  let isMetro: boolean | undefined
  if (Number.isInteger(districtId) && districtId > 0) {
    const db = getSupabaseAdmin()
    // No client means the environment is misconfigured. Leaving `isMetro`
    // undefined degrades to "delivery calculated at checkout" rather than
    // throwing, and priceCart() reports the outage properly a moment later.
    if (db) {
      const { data } = await db
        .from("store_districts")
        .select("is_metro")
        .eq("id", districtId)
        .maybeSingle()
      if (data) isMetro = data.is_metro
    }
  }

  const result = await priceCart(parsed.data, { isMetro })
  if (!result.ok) {
    return NextResponse.json({ error: result.error.message, code: result.error.code }, { status: 409 })
  }

  return NextResponse.json({ cart: result.cart, deliveryKnown: isMetro !== undefined })
}
