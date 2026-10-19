import { DHAKA_TZ, formatPhone } from "@/lib/store/format"
import type { PaymentMethod, PaymentStatus } from "@/lib/store/types"
import type { ReceiptDraft } from "./receiptMath"

/**
 * Fill a receipt from a store order, so a printed-book order does not have to
 * be typed in twice. Only the fields the receipt shows are needed; the shape
 * matches what GET /api/admin/store/orders returns.
 */
export interface OrderForReceipt {
  order_number: string
  created_at: string
  customer_name: string
  customer_phone: string
  address_line: string | null
  subtotal_bdt: number
  delivery_bdt: number
  total_bdt: number
  payment_method: PaymentMethod | string
  payment_status: PaymentStatus | string
  store_order_items: {
    product_title: string
    variant_label: string
    quantity: number
    unit_price_bdt: number | null
    line_total_bdt: number
  }[]
  store_payments: { transaction_id: string | null; created_at: string }[]
}

const METHOD_LABEL: Record<string, string> = { bkash: "bKash", nagad: "Nagad", cod: "Cash on delivery" }
const PAID_STATUSES = new Set(["verified", "paid_on_delivery"])

function dhakaDay(iso: string): string {
  // en-CA formats as yyyy-mm-dd, which is what <input type="date"> wants.
  return new Date(iso).toLocaleDateString("en-CA", { timeZone: DHAKA_TZ })
}

export function receiptFromOrder(order: OrderForReceipt, base: ReceiptDraft): ReceiptDraft {
  const items = order.store_order_items.map(it => {
    const qty = Math.max(it.quantity, 1)
    return {
      name: it.product_title,
      spec: it.variant_label,
      qty,
      rate: it.unit_price_bdt ?? Math.round(it.line_total_bdt / qty),
    }
  })
  // The order's own subtotal can include a discount the lines don't show.
  const lineSum = items.reduce((sum, it) => sum + it.qty * it.rate, 0)
  const latestPayment = [...order.store_payments]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .find(p => p.transaction_id)

  return {
    ...base,
    no: order.order_number,
    date: dhakaDay(order.created_at),
    cust: order.customer_name,
    phone: formatPhone(order.customer_phone),
    addr: order.address_line ?? "",
    items: items.length ? items : base.items,
    discount: Math.max(lineSum - order.subtotal_bdt, 0),
    delivery: order.delivery_bdt,
    paid: PAID_STATUSES.has(order.payment_status) ? order.total_bdt : 0,
    method: METHOD_LABEL[order.payment_method] ?? base.method,
    txn: latestPayment?.transaction_id ?? "",
  }
}
