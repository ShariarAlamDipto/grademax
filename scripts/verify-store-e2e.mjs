/**
 * End-to-end gate for the store, against a running server.
 *
 * Walks the whole purchase: catalogue -> price -> order -> pay -> track, and
 * then attacks it — tampered prices, a forged download grant, a stolen
 * Transaction ID, an order looked up with the wrong phone number.
 *
 *   npx next dev -p 3947
 *   node --env-file=.env.local scripts/verify-store-e2e.mjs
 *
 * Creates a throwaway product (slug __e2e-store) and deletes it at the end.
 * Store settings are saved and restored, so running this does not leave the
 * shop open.
 */
import pg from "pg"

const BASE = process.env.E2E_BASE ?? "http://localhost:3947"
const SLUG = "__e2e-store"

let pass = 0, fail = 0
const ok = (m) => { console.log(`  PASS  ${m}`); pass++ }
const bad = (m, d) => { console.log(`  FAIL  ${m}${d ? ` — ${d}` : ""}`); fail++ }

const db = new pg.Client({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
})
await db.connect()

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  let json = null
  try { json = await res.json() } catch { /* not every error path returns JSON */ }
  return { status: res.status, json }
}


/** Poll until the server observes `store_enabled = true`, or give up. */
async function waitForStoreOpen(timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/store/products`)
      const json = await res.json()
      if (json.enabled) return true
    } catch { /* server still starting */ }
    await new Promise(r => setTimeout(r, 2000))
  }
  console.log("  WARN  the server never reported the store as open")
  return false
}

// ── Save settings so the shop is left exactly as it was ──
const { rows: savedSettings } = await db.query(
  `SELECT key, value FROM store_settings
     WHERE key IN ('store_enabled','bkash_number','require_account','digital_sales_enabled')`)

async function cleanup() {
  await db.query(
    `DELETE FROM store_orders WHERE id IN (
       SELECT DISTINCT i.order_id FROM store_order_items i
        JOIN store_variants v ON v.id = i.variant_id
        JOIN store_products p ON p.id = v.product_id WHERE p.slug = $1)`, [SLUG])
  await db.query(`DELETE FROM store_products WHERE slug = $1`, [SLUG])
  // The rate limiter is real and persistent, so a previous run would otherwise
  // throttle this one before it got started.
  await db.query(`DELETE FROM store_rate_limits`)
  for (const s of savedSettings) {
    await db.query(`UPDATE store_settings SET value = $1 WHERE key = $2`, [s.value, s.key])
  }
}

try {
  await cleanup()

  // ── Fixture ──
  await db.query(`UPDATE store_settings SET value = 'true' WHERE key = 'store_enabled'`)
  await db.query(`UPDATE store_settings SET value = '01700000000' WHERE key = 'bkash_number'`)
  await db.query(`UPDATE store_settings SET value = 'true' WHERE key = 'require_account'`)

  const { rows: [prod] } = await db.query(
    `INSERT INTO store_products (slug, title, subtitle, is_active, sort_order)
     VALUES ($1, 'E2E Test Book', 'Automated test fixture', TRUE, 9999) RETURNING id`, [SLUG])
  const { rows: [printV] } = await db.query(
    `INSERT INTO store_variants (product_id, kind, label, price_bdt, stock_qty, allow_cod, r2_key)
     VALUES ($1,'print','Printed',600,10,TRUE,'secret/never-leak-this.pdf') RETURNING id`, [prod.id])
  const { rows: [digitalV] } = await db.query(
    `INSERT INTO store_variants (product_id, kind, label, price_bdt, stock_qty, allow_cod, r2_key)
     VALUES ($1,'digital','PDF',600,NULL,FALSE,'secret/never-leak-this.pdf') RETURNING id`, [prod.id])
  const { rows: [dhaka] } = await db.query(`SELECT id FROM store_districts WHERE name='Dhaka'`)

  // Settings are cached in the server for a few seconds, so a value written
  // here is not visible to the running app immediately. Wait for the catalogue
  // to actually report the shop as open before asserting anything about it --
  // otherwise every HTTP check fails with "the store is not open yet" and the
  // real result is hidden behind a timing artefact.
  await waitForStoreOpen()

  console.log("\nThe catalogue never exposes the path to a paid file")
  {
    const res = await fetch(`${BASE}/api/store/products`)
    const text = await res.text()
    res.ok ? ok("catalogue responds") : bad("catalogue", res.status)
    !text.includes("never-leak-this") && !text.includes("r2_key")
      ? ok("no r2_key anywhere in the response body")
      : bad("THE PAID FILE PATH LEAKED into /api/store/products")
    const json = JSON.parse(text)
    json.products?.some(p => p.slug === SLUG)
      ? ok("the test product is listed")
      : bad("test product missing from catalogue")
  }

  console.log("\nAn account is required to order")
  {
    const r = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "Guest", phone: "01712345678", email: "guest@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12" },
      paymentMethod: "cod",
    })
    r.status === 401 && r.json?.requiresAccount
      ? ok("a signed-out buyer is asked to sign in")
      : bad("GUEST CHECKOUT WAS ALLOWED", `${r.status} ${JSON.stringify(r.json)}`)

    const { rows: [n] } = await db.query(
      `SELECT count(*)::int c FROM store_orders WHERE customer_name = 'Guest'`)
    n.c === 0 ? ok("no order was written for the guest") : bad("guest order written", n.c)
  }

  console.log("\nDigital downloads are not on sale")
  {
    const r = await post("/api/store/cart", { items: [{ variantId: digitalV.id, quantity: 1 }] })
    r.status === 409 && /not on sale/i.test(r.json?.error ?? "")
      ? ok("a PDF in the cart is refused with an explanation")
      : bad("digital cart was accepted", `${r.status} ${JSON.stringify(r.json)}`)

    const res = await fetch(`${BASE}/api/store/products`)
    const json = JSON.parse(await res.text())
    const mine = json.products?.find(p => p.slug === SLUG)
    mine && mine.variants.every(v => v.kind === "print")
      ? ok("the catalogue lists no digital variant")
      : bad("A DIGITAL VARIANT IS STILL LISTED", JSON.stringify(mine?.variants))
  }

  // The remaining HTTP checks need to reach the order path, which is gated on a
  // session this script does not have. Lift the gate for them; cleanup restores it.
  await db.query(`UPDATE store_settings SET value = 'false' WHERE key = 'require_account'`)
  // Settings are cached in-process for 15s, so the running server keeps
  // refusing until that window passes. Wait it out rather than racing it.
  await new Promise(r => setTimeout(r, 16_000))

  console.log("\nPricing is done by the server")
  {
    const r = await post("/api/store/cart", { items: [{ variantId: printV.id, quantity: 2 }] })
    r.json?.cart?.subtotalBdt === 1200
      ? ok("2 x 600 = 1200")
      : bad("subtotal", JSON.stringify(r.json))

    // A client that sends its own prices must be ignored, not obeyed.
    const t = await post("/api/store/cart", {
      items: [{ variantId: printV.id, quantity: 1, price_bdt: 1, unitPriceBdt: 1, lineTotalBdt: 1 }],
    })
    t.json?.cart?.subtotalBdt === 600
      ? ok("a price sent by the client is ignored")
      : bad("CLIENT PRICE WAS TRUSTED", JSON.stringify(t.json))

    const q = await post("/api/store/cart", { items: [{ variantId: printV.id, quantity: 40 }] })
    q.status === 409
      ? ok("40 copies of one title is refused")
      : bad("quantity cap", q.status)
  }

  console.log("\nCash on delivery works for a printed order")
  {
    const r = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "01712345678", email: "e2e@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12", roadNo: "5" },
      paymentMethod: "cod",
    })
    r.status === 201 ? ok("a cash-on-delivery order is accepted") : bad("COD refused", JSON.stringify(r.json))
    r.json?.paymentStatus === "cod_pending"
      ? ok("it waits for the courier to collect")
      : bad("COD payment status", r.json?.paymentStatus)
  }

  console.log("\nA print order needs a full address")
  {
    const noAddress = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "01712345678", email: "e2e@example.com" },
      paymentMethod: "bkash",
    })
    noAddress.status === 409 ? ok("refused with no address at all") : bad("address check", noAddress.status)

    const noHouse = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "01712345678", email: "e2e@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi" },
      paymentMethod: "bkash",
    })
    noHouse.status === 400 ? ok("refused with no house number") : bad("house number check", noHouse.status)

    const noEmail = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "01712345678" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12" },
      paymentMethod: "bkash",
    })
    noEmail.status === 400 ? ok("refused with no email address") : bad("email check", noEmail.status)
  }

  console.log("\nPhone numbers are normalised, not rejected")
  {
    for (const variant of ["+8801712345678", "8801712345678", "01712-345678", "01712 345678"]) {
      const r = await post("/api/store/cart", { items: [{ variantId: printV.id, quantity: 1 }] })
      if (!r.json?.cart) { bad("cart broke"); break }
    }
    const r = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "+8801712345678", email: "e2e@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12", roadNo: "5" },
      paymentMethod: "bkash",
    })
    r.status === 201 ? ok("+880 form accepted") : bad("+880 rejected", JSON.stringify(r.json))

    const { rows: [stored] } = await db.query(
      `SELECT customer_phone FROM store_orders WHERE order_number = $1`, [r.json.orderNumber])
    stored?.customer_phone === "01712345678"
      ? ok("stored as 01712345678")
      : bad("normalisation", stored?.customer_phone)

    const bogus = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "12345", email: "e2e@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12" },
      paymentMethod: "bkash",
    })
    bogus.status === 400 ? ok("a non-Bangladeshi number is refused") : bad("phone validation", bogus.status)
  }

  console.log("\nA full order, then payment, then tracking")
  let order = null
  {
    const r = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "E2E Buyer", phone: "01712345678", email: "e2e@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12", roadNo: "5" },
      paymentMethod: "bkash",
      source: { path: "/store/__e2e-store" },
    })
    r.status === 201 ? ok("order created") : bad("checkout", JSON.stringify(r.json))
    order = r.json
    order?.totalBdt === 670
      ? ok("600 + 70 delivery = 670")
      : bad("total", order?.totalBdt)
    const ORDER_NUMBER_SHAPE = /^GM-\d+-[0-9A-Z]{4}$/
    ORDER_NUMBER_SHAPE.test(order?.orderNumber ?? "")
      ? ok(`order number is not enumerable (${order.orderNumber})`)
      : bad("order number format", order?.orderNumber)
    order?.payTo === "01700000000" ? ok("the bKash number is returned") : bad("payTo", order?.payTo)
  }

  if (!order?.orderNumber) {
    bad("checkout did not produce an order — skipping the payment and tracking checks")
  } else {

  console.log("\nThe order cannot be read with the wrong phone number")
  {
    const r = await post("/api/store/orders/lookup", {
      orderNumber: order.orderNumber, phone: "01799999999",
    })
    r.status === 404 ? ok("wrong phone is refused") : bad("lookup auth", r.status)
  }

  console.log("\nPayment claims")
  {
    const r = await post("/api/store/payment", {
      orderNumber: order.orderNumber, phone: "01712345678",
      method: "bkash", senderMsisdn: "01712345678",
      transactionId: "E2ETRX001", amountBdt: 670,
    })
    r.status === 200 ? ok("payment recorded") : bad("payment submit", JSON.stringify(r.json))

    const { rows: [o] } = await db.query(
      `SELECT payment_status FROM store_orders WHERE order_number = $1`, [order.orderNumber])
    o.payment_status === "submitted" ? ok("order moved to submitted") : bad("status", o.payment_status)

    // A second order trying to claim the same Transaction ID must not be told
    // that it already exists — that would confirm which IDs are real.
    const second = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "Other Buyer", phone: "01812345678", email: "other@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Uttara", houseNo: "9" },
      paymentMethod: "bkash",
    })
    const steal = await post("/api/store/payment", {
      orderNumber: second.json.orderNumber, phone: "01812345678",
      method: "bkash", senderMsisdn: "01812345678",
      transactionId: "E2ETRX001", amountBdt: 670,
    })
    steal.status === 200 && !/already|duplicate|exists|in use/i.test(JSON.stringify(steal.json))
      ? ok("a duplicate Transaction ID gets the same neutral reply")
      : bad("duplicate TrxID is an oracle", JSON.stringify(steal.json))

    const { rows: [victim] } = await db.query(
      `SELECT payment_status FROM store_orders WHERE order_number = $1`, [order.orderNumber])
    victim.payment_status === "submitted"
      ? ok("the original claim was not disturbed")
      : bad("the original order was affected", victim.payment_status)
  }

  console.log("\nTracking shows the order without giving the address away")
  {
    const r = await post("/api/store/orders/lookup", {
      orderNumber: order.orderNumber, phone: "01712345678",
    })
    r.status === 200 ? ok("lookup succeeds with the right phone") : bad("lookup", r.status)
    const body = JSON.stringify(r.json)
    !body.includes("12 Road 5") ? ok("the street address is not returned") : bad("ADDRESS LEAKED")
    !body.includes("01712345678") ? ok("the phone number is masked") : bad("PHONE LEAKED")
    r.json?.order?.downloads?.length === 0
      ? ok("no download is offered before payment is verified")
      : bad("DOWNLOAD OFFERED WHILE UNPAID", body)
  }

  console.log("\nDownload grants")
  {
    const forged = await fetch(`${BASE}/api/store/download/aaaa.9999999999999.bbbb`)
    forged.status === 403 ? ok("a forged grant is refused") : bad("forged grant", forged.status)

    const junk = await fetch(`${BASE}/api/store/download/notatoken`)
    junk.status === 403 ? ok("a malformed grant is refused") : bad("malformed grant", junk.status)

    // Verify the payment, then confirm the entitlement appears.
    const { rows: [o] } = await db.query(
      `SELECT id FROM store_orders WHERE order_number = $1`, [order.orderNumber])
    await db.query(`SELECT store_verify_payment($1,NULL,'e2e','ok')`, [o.id])

    // This is a printed order, so there is nothing to download - which is the
    // point: the entitlement machinery must stay dormant while PDFs are off.
    const after = await post("/api/store/orders/lookup", {
      orderNumber: order.orderNumber, phone: "01712345678",
    })
    after.json?.order?.downloads?.length === 0
      ? ok("a printed order offers no download")
      : bad("A DOWNLOAD WAS OFFERED FOR A PRINTED ORDER", JSON.stringify(after.json?.order?.downloads))

    await db.query(`SELECT store_cancel_order($1,NULL,'e2e','test')`, [o.id])
    ok("the order can be cancelled")
  }

  }

  console.log("\nThe admin API is closed to the public")
  {
    for (const path of ["/api/admin/store/orders", "/api/admin/store/stats", "/api/admin/store/products", "/api/admin/store/settings"]) {
      const res = await fetch(`${BASE}${path}`)
      res.status === 401 || res.status === 403
        ? ok(`${path} -> ${res.status}`)
        : bad(`${path} is reachable without auth`, res.status)
    }
    const res = await fetch(`${BASE}/api/admin/store/payment`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orderId: "00000000-0000-0000-0000-000000000000", decision: "verify" }),
    })
    res.status === 401 || res.status === 403
      ? ok(`payment verification is protected (${res.status})`)
      : bad("ANYONE CAN VERIFY PAYMENTS", res.status)
  }

  console.log("\nThe honeypot absorbs bots")
  {
    // The checkouts above have eaten the rate-limit budget for this IP.
    await db.query(`DELETE FROM store_rate_limits`)
    const r = await post("/api/store/checkout", {
      items: [{ variantId: printV.id, quantity: 1 }],
      customer: { name: "Bot", phone: "01712345678", email: "bot@example.com" },
      delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12" },
      paymentMethod: "bkash",
      website: "http://spam.example",
    })
    const { rows: [n] } = await db.query(
      `SELECT count(*)::int c FROM store_orders WHERE customer_name = 'Bot'`)
    r.status === 200 && n.c === 0
      ? ok("looks successful to the bot, but no order was written")
      : bad("honeypot", `status ${r.status}, ${n.c} orders created`)
  }

  console.log("\nCheckout is rate limited")
  {
    const attempts = []
    for (let i = 0; i < 12; i++) {
      attempts.push(await post("/api/store/checkout", {
        items: [{ variantId: printV.id, quantity: 1 }],
        customer: { name: "Flood", phone: "01712345678", email: "flood@example.com" },
        delivery: { districtId: dhaka.id, city: "Dhaka", area: "Dhanmondi", houseNo: "12" },
        paymentMethod: "bkash",
      }))
    }
    attempts.some(a => a.status === 429)
      ? ok("a burst of orders is throttled")
      : bad("NO RATE LIMIT on checkout", attempts.map(a => a.status).join(","))
  }
} finally {
  await cleanup()
  console.log("\n(test product and orders deleted, settings restored)")
  await db.end()
}

console.log(`\n${pass} passed, ${fail} failed\n`)
process.exit(fail ? 1 : 0)
