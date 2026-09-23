/**
 * Telegram notification for a new order.
 *
 * The shop is run by one person, and an order that nobody sees until they next
 * open the admin page is an order that ships late. This pushes each new order
 * to a phone the moment it is placed.
 *
 * Two rules govern everything here:
 *
 *  1. **It must never break checkout.** A notification is a courtesy to the
 *    shopkeeper; the buyer's order is the thing that matters. Every failure --
 *    no token configured, Telegram down, a network timeout -- is swallowed and
 *    logged, exactly as `recordOrderEvent` treats its own failures.
 *
 *  2. **Customer text is untrusted.** Names, addresses and order notes are
 *    typed by strangers and are rendered here as Telegram HTML, so every
 *    interpolated value is escaped. Telegram would otherwise reject the whole
 *    message on a stray "<", which would silently cost the notification.
 *
 * Configure with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. With either missing
 * the notifier turns itself off and checkout is unaffected.
 */
import type { OrderView } from "./orders"

const TELEGRAM_TIMEOUT_MS = 4000

/** Escapes the five characters Telegram's HTML parse mode cares about. */
function esc(value: string | null | undefined): string {
  if (!value) return ""
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}

function taka(amount: number): string {
  return `৳${amount.toLocaleString("en-US")}`
}

const PAYMENT_LABELS: Record<string, string> = {
  cod: "Cash on delivery",
  bkash: "bKash",
  nagad: "Nagad",
}

/**
 * The delivery address as a courier would need it.
 *
 * `address_line` is the canonical printable line, composed by
 * `composeAddressLine` when the order was written ("House 12, Road 5, ..."), so
 * it is preferred. The separate parts are only assembled as a fallback for
 * orders stored before that column was populated.
 */
function addressLines(order: OrderView): string[] {
  if (order.address_line?.trim()) {
    return [order.address_line.trim(), order.district_name ?? ""]
      .map(part => part.trim())
      .filter(Boolean)
  }
  const street = [
    order.house_no ? `House ${order.house_no}` : "",
    order.road_no ? `Road ${order.road_no}` : "",
  ].filter(Boolean).join(", ")
  const place = [order.area, order.city, order.district_name].filter(Boolean).join(", ")
  return [street, place, order.landmark ? `Near ${order.landmark}` : "", order.postcode]
    .map(part => (part ?? "").trim())
    .filter(Boolean)
}

export function buildOrderMessage(order: OrderView): string {
  const lines: string[] = []
  lines.push(`🛒 <b>New order ${esc(order.order_number)}</b>`)
  lines.push("")

  for (const item of order.items) {
    lines.push(`• ${item.quantity} × ${esc(item.product_title)} — ${taka(item.line_total_bdt)}`)
  }

  lines.push("")
  if (order.delivery_bdt > 0) {
    lines.push(`Subtotal ${taka(order.subtotal_bdt)} + delivery ${taka(order.delivery_bdt)}`)
  }
  lines.push(`<b>Total ${taka(order.total_bdt)}</b> — ${esc(PAYMENT_LABELS[order.payment_method] ?? order.payment_method)}`)

  lines.push("")
  lines.push(`<b>${esc(order.customer_name)}</b>`)
  lines.push(`📞 ${esc(order.customer_phone)}${order.alt_phone ? ` / ${esc(order.alt_phone)}` : ""}`)
  if (order.customer_email) lines.push(`✉️ ${esc(order.customer_email)}`)

  const address = addressLines(order)
  if (address.length > 0) {
    lines.push("")
    lines.push(address.map(esc).join("\n"))
  }

  return lines.join("\n")
}

/**
 * Sends the message. Resolves to whether it was delivered; never rejects, so a
 * caller can `await` it without guarding.
 */
export async function notifyNewOrder(order: OrderView): Promise<boolean> {
  const token = process.env.TELEGRAM_BOT_TOKEN?.trim()
  const chatId = process.env.TELEGRAM_CHAT_ID?.trim()
  if (!token || !chatId) return false

  try {
    const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: buildOrderMessage(order),
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
      // Checkout has already succeeded by the time this runs, so the buyer is
      // waiting on it. A slow Telegram must not hold the response open.
      signal: AbortSignal.timeout(TELEGRAM_TIMEOUT_MS),
    })

    if (!response.ok) {
      const body = await response.text().catch(() => "")
      console.error(`[store/notify] Telegram refused the message (${response.status}): ${body.slice(0, 300)}`)
      return false
    }
    return true
  } catch (error: unknown) {
    const reason = error instanceof Error ? error.message : String(error)
    console.error(`[store/notify] could not send the order notification: ${reason}`)
    return false
  }
}
