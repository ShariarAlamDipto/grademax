import { NextRequest, NextResponse } from "next/server"
import { requireAuth } from "@/lib/apiAuth"
import { createOrder } from "@/lib/store/orders"
import { checkoutSchema } from "@/lib/store/schemas"
import { getSettings } from "@/lib/store/settings"
import { checkRateLimitByIp } from "@/lib/store/rateLimit"

/**
 * POST /api/store/checkout — place an order.
 *
 * An account is required. Orders are shipped by hand and followed up by phone,
 * so every order needs an owner who can see its status and be contacted; guest
 * checkout would also make the order history impossible to show anyone.
 *
 * It is still rate limited, honeypotted and schema-validated, and it delegates
 * every price and stock decision to a single database transaction — a signed-in
 * buyer is not a trusted one.
 */
export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  const settings = await getSettings()
  if (!settings.storeEnabled) {
    return NextResponse.json({ error: "The store is not open yet." }, { status: 503 })
  }

  // An account is required, so this runs before anything else reads the body.
  let userId: string | null = null
  if (settings.requireAccount) {
    const auth = await requireAuth()
    if ("error" in auth) {
      return NextResponse.json(
        { error: "Please sign in to place your order.", requiresAccount: true },
        { status: 401 }
      )
    }
    userId = auth.user.id
  }

  if (!(await checkRateLimitByIp("checkout"))) {
    return NextResponse.json(
      { error: "Too many orders from this connection. Please wait a few minutes and try again." },
      { status: 429 }
    )
  }

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 })
  }

  const parsed = checkoutSchema.safeParse(body)
  if (!parsed.success) {
    const first = parsed.error.issues[0]
    return NextResponse.json(
      { error: first?.message ?? "Please check the form and try again.", field: first?.path.join(".") },
      { status: 400 }
    )
  }
  const input = parsed.data

  // Honeypot: a hidden field only an automated submitter fills in. Answer 200
  // so the bot records a success and does not retry with a different shape.
  if (input.website) {
    return NextResponse.json({ orderNumber: "GM-000000-XXXX", totalBdt: 0 })
  }

  const result = await createOrder(input, userId)
  if (!result.ok) {
    return NextResponse.json({ error: result.message, code: result.code }, { status: 409 })
  }

  const { order } = result
  return NextResponse.json({
    orderNumber: order.orderNumber,
    totalBdt: order.totalBdt,
    subtotalBdt: order.subtotalBdt,
    deliveryBdt: order.deliveryBdt,
    hasDigital: order.hasDigital,
    hasPrint: order.hasPrint,
    paymentMethod: input.paymentMethod,
    paymentStatus: order.paymentStatus,
    payTo: input.paymentMethod === "bkash" ? settings.bkashNumber
         : input.paymentMethod === "nagad" ? settings.nagadNumber
         : null,
    instructions: settings.paymentInstructions,
    slaHours: settings.verificationSlaHours,
  }, { status: 201 })
}
