/**
 * Shared store types.
 *
 * Every amount in the store is an INTEGER number of Taka. There are no
 * fractional prices, so there is no reason to invite float rounding bugs.
 */

export type VariantKind = "print" | "digital"

export type PaymentMethod = "bkash" | "nagad" | "cod"

export type PaymentStatus =
  | "awaiting_payment"
  | "submitted"
  | "verified"
  | "rejected"
  | "cod_pending"
  | "paid_on_delivery"
  | "refunded"

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "packed"
  | "shipped"
  | "delivered"
  | "cancelled"

/** Columns that are safe to send to a browser. `r2_key` is deliberately absent. */
export interface PublicVariant {
  id: string
  kind: VariantKind
  label: string
  price_bdt: number
  compare_at_bdt: number | null
  in_stock: boolean
  stock_qty: number | null
  allow_cod: boolean
  page_count: number | null
}

export interface PublicProduct {
  id: string
  slug: string
  title: string
  subtitle: string | null
  description: string | null
  subject_code: string | null
  spec_summary: string | null
  cover_image_url: string | null
  preview_url: string | null
  preview_pages: number | null
  variants: PublicVariant[]
}

/** What the browser sends. Note there is no price — the server sets that. */
export interface CartLineInput {
  variantId: string
  quantity: number
}

export interface PricedLine {
  variantId: string
  productId: string
  productTitle: string
  variantLabel: string
  kind: VariantKind
  unitPriceBdt: number
  quantity: number
  lineTotalBdt: number
}

export interface PricedCart {
  lines: PricedLine[]
  subtotalBdt: number
  deliveryBdt: number
  discountBdt: number
  totalBdt: number
  hasPrint: boolean
  hasDigital: boolean
  /** Methods this cart is actually allowed to use. */
  allowedPaymentMethods: PaymentMethod[]
}

export interface District {
  id: number
  name: string
  division: string
  is_metro: boolean
}

export const ORDER_STATUS_FLOW: OrderStatus[] = [
  "pending", "confirmed", "packed", "shipped", "delivered",
]

export const PAYMENT_STATUS_LABEL: Record<PaymentStatus, string> = {
  awaiting_payment: "Awaiting payment",
  submitted: "Payment submitted — checking",
  verified: "Payment verified",
  rejected: "Payment rejected",
  cod_pending: "Cash on delivery",
  paid_on_delivery: "Paid on delivery",
  refunded: "Refunded",
}

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  packed: "Packed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
}
