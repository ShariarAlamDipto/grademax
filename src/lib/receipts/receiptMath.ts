/**
 * The arithmetic behind the A4 booklet-printing receipt in /admin/receipts.
 *
 * Every amount is a whole number of Taka, as in the store. The editor keeps
 * raw form strings around, so each amount is passed through toAmount before
 * it is added up — a stray letter or minus sign must not reach the total.
 */

export interface ReceiptItem {
  name: string
  spec: string
  qty: number
  rate: number
}

export interface ReceiptDraft {
  shop: string
  shopSub: string
  no: string
  date: string // yyyy-mm-dd
  ready: string // yyyy-mm-dd or ""
  cust: string
  phone: string
  addr: string
  items: ReceiptItem[]
  discount: number
  delivery: number
  paid: number
  method: string
  txn: string
  note: string
}

export interface ReceiptLine extends ReceiptItem {
  amount: number
}

export interface ReceiptTotals {
  lines: ReceiptLine[]
  copies: number
  subtotal: number
  discount: number
  delivery: number
  total: number
  paid: number
  /** Total minus paid. Negative when the customer paid more (change returned). */
  balance: number
}

export const PAYMENT_METHODS = ["Cash", "bKash", "Nagad", "Rocket", "Bank transfer", "Cash on delivery"] as const

export const DEFAULT_RECEIPT_NOTE =
  "Balance to be paid on collection. Please bring this receipt. Booklets not collected within 30 days may be recycled."

export const emptyItem = (): ReceiptItem => ({ name: "", spec: "", qty: 1, rate: 0 })

export function blankReceipt(today: string): ReceiptDraft {
  return {
    shop: "GradeMax Print",
    shopSub: "Dhaka, Bangladesh · grademax.me",
    no: "",
    date: today,
    ready: "",
    cust: "",
    phone: "",
    addr: "",
    items: [emptyItem()],
    discount: 0,
    delivery: 0,
    paid: 0,
    method: "Cash",
    txn: "",
    note: DEFAULT_RECEIPT_NOTE,
  }
}

/** A non-negative whole number of Taka; anything unreadable counts as 0. */
export function toAmount(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value)
  return Number.isFinite(n) && n > 0 ? Math.round(n) : 0
}

export function computeTotals(draft: ReceiptDraft): ReceiptTotals {
  const lines = draft.items
    .filter(it => it.name.trim() || toAmount(it.rate) > 0)
    .map(it => {
      const qty = toAmount(it.qty)
      const rate = toAmount(it.rate)
      return { ...it, qty, rate, amount: qty * rate }
    })
  const subtotal = lines.reduce((sum, l) => sum + l.amount, 0)
  const copies = lines.reduce((sum, l) => sum + l.qty, 0)
  const discount = Math.min(toAmount(draft.discount), subtotal)
  const delivery = toAmount(draft.delivery)
  const total = subtotal - discount + delivery
  const paid = toAmount(draft.paid)
  return { lines, copies, subtotal, discount, delivery, total, paid, balance: total - paid }
}

export function paymentStamp(t: ReceiptTotals): "paid" | "partly" | null {
  if (t.total <= 0) return null
  if (t.balance <= 0) return "paid"
  return t.paid > 0 ? "partly" : null
}

const ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
  "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
const TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
const GROUPS: [number, string][] = [[10_000_000, "Crore"], [100_000, "Lakh"], [1_000, "Thousand"], [100, "Hundred"]]

function underHundred(n: number): string {
  if (n < 20) return ONES[n]
  return TENS[Math.floor(n / 10)] + (n % 10 ? `-${ONES[n % 10]}` : "")
}

/** "One Lakh Twenty-Five Thousand" — South-Asian grouping, as written on a cash memo. */
export function takaInWords(amount: number): string {
  let n = toAmount(amount)
  if (n === 0) return "Zero"
  const parts: string[] = []
  for (const [size, word] of GROUPS) {
    if (n >= size) {
      const count = Math.floor(n / size)
      parts.push(`${count >= 100 ? takaInWords(count) : underHundred(count)} ${word}`)
      n %= size
    }
  }
  if (n) parts.push(underHundred(n))
  return parts.join(" ")
}
