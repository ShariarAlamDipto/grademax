import { test } from "node:test"
import assert from "node:assert/strict"

import { buildOrderMessage } from "../src/lib/store/notify"
import type { OrderView } from "../src/lib/store/orders"

function order(overrides: Partial<OrderView> = {}): OrderView {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    order_number: "GM-1042",
    customer_name: "Rafiq Hasan",
    customer_phone: "01712345678",
    customer_email: "rafiq@example.com",
    district_name: "Dhaka",
    city: "Dhaka",
    area: "Dhanmondi",
    address_line: "House 12, Road 5, Dhanmondi, Dhaka",
    house_no: "12",
    road_no: "5",
    landmark: "Opposite the mosque",
    alt_phone: null,
    postcode: "1209",
    has_print: true,
    has_digital: false,
    subtotal_bdt: 1200,
    delivery_bdt: 70,
    discount_bdt: 0,
    total_bdt: 1270,
    payment_method: "cod",
    payment_status: "cod_pending",
    order_status: "pending",
    courier_name: null,
    tracking_code: null,
    created_at: "2026-09-23T10:00:00Z",
    items: [
      {
        id: "item-1",
        product_title: "Mathematics B — Chapterwise Workbook, Part 1",
        variant_label: "Printed copy — spiral bound",
        variant_kind: "print",
        unit_price_bdt: 600,
        quantity: 2,
        line_total_bdt: 1200,
      },
    ],
    ...overrides,
  }
}

test("includes the order number, items, total and payment method", () => {
  const message = buildOrderMessage(order())
  assert.match(message, /GM-1042/)
  assert.match(message, /2 × Mathematics B/)
  assert.match(message, /৳1,200/)
  assert.match(message, /৳1,270/)
  assert.match(message, /Cash on delivery/)
})

test("shows the delivery charge only when one was applied", () => {
  assert.match(buildOrderMessage(order()), /Subtotal ৳1,200 \+ delivery ৳70/)
  // "Cash on delivery" contains the word too, so it is the subtotal line that
  // has to be absent, not every mention of delivery.
  const free = buildOrderMessage(order({ delivery_bdt: 0, total_bdt: 1200 }))
  assert.doesNotMatch(free, /Subtotal/)
})

test("escapes customer-supplied text so Telegram cannot be fed markup", () => {
  // A name is typed by a stranger. Unescaped, "<b>" would either format the
  // message or make Telegram reject it outright, losing the notification.
  const message = buildOrderMessage(order({
    customer_name: "<b>Bold</b> & \"quoted\"",
    landmark: "next to <script>alert(1)</script>",
  }))
  assert.doesNotMatch(message, /<b>Bold<\/b>/)
  assert.doesNotMatch(message, /<script>/)
  assert.match(message, /&lt;b&gt;Bold&lt;\/b&gt; &amp; &quot;quoted&quot;/)
})

test("prefers the composed address line a courier would print", () => {
  assert.match(buildOrderMessage(order()), /House 12, Road 5, Dhanmondi, Dhaka/)
})

test("falls back to the separate parts, omitting any that are missing", () => {
  const message = buildOrderMessage(order({
    address_line: null,
    house_no: null, road_no: null, landmark: null, postcode: null,
    area: "Dhanmondi", city: "Dhaka", district_name: "Dhaka",
  }))
  assert.doesNotMatch(message, /\n\n\n/)
  assert.doesNotMatch(message, /House |Road /)
  assert.match(message, /Dhanmondi, Dhaka, Dhaka/)
})

test("lists every line of a multi-item order", () => {
  const message = buildOrderMessage(order({
    items: [
      { id: "a", product_title: "Maths B Part 1", variant_label: "Print", variant_kind: "print", unit_price_bdt: 600, quantity: 1, line_total_bdt: 600 },
      { id: "b", product_title: "Further Pure Mathematics", variant_label: "Print", variant_kind: "print", unit_price_bdt: 800, quantity: 1, line_total_bdt: 800 },
    ],
    subtotal_bdt: 1400, total_bdt: 1470,
  }))
  assert.match(message, /1 × Maths B Part 1/)
  assert.match(message, /1 × Further Pure Mathematics/)
})
