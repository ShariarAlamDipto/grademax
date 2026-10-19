import { NextRequest, NextResponse } from "next/server"
import { getOrderByNumber, submitPayment } from "@/lib/store/orders"
import { paymentSubmitSchema } from "@/lib/store/schemas"
import { checkRateLimitByIp } from "@/lib/store/rateLimit"
import { phoneMatches } from "@/lib/store/phone"

/**
 * POST /api/store/payment — the buyer reports a bKash/Nagad transaction.
 *
 * The response is deliberately uniform. A distinct "that Transaction ID is
 * already used" reply would be an oracle: it confirms which IDs exist, and it
 * lets somebody block a stranger's order by claiming their receipt first.
 * Collisions are recorded for the admin to see, and the buyer is simply told
 * the payment is being checked.
 */
export const dynamic = "force-dynamic"

const UNIFORM_OK = {
  ok: true,
  message: "Payment recorded. We are checking it now and will confirm shortly.",
}

export async function POST(req: NextRequest) {
  if (!(await checkRateLimitByIp("paymentSubmit"))) {
    return NextResponse.json(
      { error: "Too many attempts. Please wait a few minutes." },
      { status: 429 }
    )
  }

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 })
  }

  const parsed = paymentSubmitSchema.safeParse(body)
  if (!parsed.success) {
    const first = parsed.error.issues[0]
    return NextResponse.json(
      { error: first?.message ?? "Please check the details and try again.", field: first?.path.join(".") },
      { status: 400 }
    )
  }
  const input = parsed.data

  const order = await getOrderByNumber(input.orderNumber)
  // The order number alone is not enough to attach a payment: the phone number
  // on the order must match too. Same generic reply either way so this cannot
  // be used to test whether an order number exists.
  if (!order || !phoneMatches(order.customer_phone, input.phone)) {
    return NextResponse.json(
      { error: "We could not find an order with that number and phone number." },
      { status: 404 }
    )
  }

  if (order.payment_status === "verified") {
    return NextResponse.json({ ok: true, message: "This order is already paid." })
  }

  await submitPayment({
    orderId: order.id,
    method: input.method,
    senderMsisdn: input.senderMsisdn,
    transactionId: input.transactionId,
    amountBdt: input.amountBdt ?? order.total_bdt,
  })

  // Every outcome below a hard validation failure answers identically.
  return NextResponse.json(UNIFORM_OK)
}
