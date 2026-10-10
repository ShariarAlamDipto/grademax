import { test } from "node:test"
import assert from "node:assert/strict"
import {
  blankReceipt,
  computeTotals,
  paymentStamp,
  takaInWords,
  toAmount,
  type ReceiptDraft,
} from "../src/lib/receipts/receiptMath"
import { receiptFromOrder, type OrderForReceipt } from "../src/lib/receipts/fromOrder"

const draft = (over: Partial<ReceiptDraft> = {}): ReceiptDraft => ({
  ...blankReceipt("2026-10-03"),
  items: [
    { name: "FPM Workbook", spec: "A4 · 388 pp", qty: 2, rate: 1250 },
    { name: "Mark scheme booklet", spec: "A5", qty: 3, rate: 180 },
  ],
  discount: 150,
  delivery: 80,
  paid: 1500,
  ...over,
})

test("toAmount keeps non-negative whole Taka and rejects junk", () => {
  assert.equal(toAmount("1250"), 1250)
  assert.equal(toAmount(12.6), 13)
  assert.equal(toAmount(-5), 0)
  assert.equal(toAmount("abc"), 0)
  assert.equal(toAmount(undefined), 0)
  assert.equal(toAmount(Infinity), 0)
})

test("total payable is subtotal minus discount plus delivery", () => {
  const t = computeTotals(draft())
  assert.equal(t.subtotal, 2 * 1250 + 3 * 180)
  assert.equal(t.copies, 5)
  assert.equal(t.total, 3040 - 150 + 80)
  assert.equal(t.balance, 2970 - 1500)
  assert.deepEqual(t.lines.map(l => l.amount), [2500, 540])
})

test("a discount larger than the subtotal cannot make the total negative", () => {
  const t = computeTotals(draft({ discount: 99999, delivery: 0 }))
  assert.equal(t.discount, t.subtotal)
  assert.equal(t.total, 0)
})

test("empty booklet rows are left off the receipt", () => {
  const t = computeTotals(draft({ items: [{ name: "", spec: "", qty: 1, rate: 0 }, { name: "A", spec: "", qty: 1, rate: 10 }] }))
  assert.equal(t.lines.length, 1)
  assert.equal(t.subtotal, 10)
})

test("overpayment shows as a negative balance (change returned)", () => {
  const t = computeTotals(draft({ paid: 5000 }))
  assert.equal(t.balance, 2970 - 5000)
})

test("the payment stamp follows what has been paid", () => {
  assert.equal(paymentStamp(computeTotals(draft({ paid: 0 }))), null)
  assert.equal(paymentStamp(computeTotals(draft({ paid: 100 }))), "partly")
  assert.equal(paymentStamp(computeTotals(draft({ paid: 2970 }))), "paid")
  assert.equal(paymentStamp(computeTotals(draft({ items: [], paid: 0 }))), null)
})

test("Taka in words uses lakh and crore", () => {
  assert.equal(takaInWords(0), "Zero")
  assert.equal(takaInWords(15), "Fifteen")
  assert.equal(takaInWords(2970), "Two Thousand Nine Hundred Seventy")
  assert.equal(takaInWords(125000), "One Lakh Twenty-Five Thousand")
  assert.equal(takaInWords(23456789), "Two Crore Thirty-Four Lakh Fifty-Six Thousand Seven Hundred Eighty-Nine")
})

const order = (over: Partial<OrderForReceipt> = {}): OrderForReceipt => ({
  order_number: "GM-1042",
  created_at: "2026-10-02T20:30:00Z",
  customer_name: "Rahim Uddin",
  customer_phone: "01712345678",
  address_line: "House 4, Road 2, Dhanmondi, Dhaka",
  subtotal_bdt: 2500,
  delivery_bdt: 80,
  total_bdt: 2580,
  payment_method: "bkash",
  payment_status: "verified",
  store_order_items: [
    { product_title: "FPM Workbook", variant_label: "Printed book", quantity: 2, unit_price_bdt: 1250, line_total_bdt: 2500 },
  ],
  store_payments: [{ transaction_id: "8N7A6B5C", created_at: "2026-10-02T21:00:00Z" }],
  ...over,
})

test("an order becomes a receipt with its lines, delivery and payment", () => {
  const r = receiptFromOrder(order(), blankReceipt("2026-10-03"))
  assert.equal(r.no, "GM-1042")
  assert.equal(r.date, "2026-10-03") // 20:30 UTC is the next morning in Dhaka
  assert.equal(r.cust, "Rahim Uddin")
  assert.equal(r.phone, "01712 345678")
  assert.deepEqual(r.items, [{ name: "FPM Workbook", spec: "Printed book", qty: 2, rate: 1250 }])
  assert.equal(r.delivery, 80)
  assert.equal(r.paid, 2580)
  assert.equal(r.method, "bKash")
  assert.equal(r.txn, "8N7A6B5C")
  assert.equal(computeTotals(r).total, 2580)
})

test("an unpaid cash-on-delivery order has nothing paid yet", () => {
  const r = receiptFromOrder(order({ payment_method: "cod", payment_status: "cod_pending", store_payments: [] }), blankReceipt("2026-10-03"))
  assert.equal(r.paid, 0)
  assert.equal(r.method, "Cash on delivery")
  assert.equal(r.txn, "")
})

test("an order line without a unit price falls back to its line total", () => {
  const r = receiptFromOrder(order({
    store_order_items: [{ product_title: "X", variant_label: "PDF", quantity: 2, unit_price_bdt: null, line_total_bdt: 900 }],
  }), blankReceipt("2026-10-03"))
  assert.equal(r.items[0].rate, 450)
})
