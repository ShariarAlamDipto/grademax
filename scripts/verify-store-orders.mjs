/**
 * Order creation under concurrency, and idempotent transitions.
 *
 * The stock race cannot be tested inside a single transaction, so this creates
 * real rows on two separate connections and deletes them at the end. Everything
 * it touches is namespaced under the slug `__test-concurrency`.
 *
 *   node --env-file=.env.local scripts/verify-store-orders.mjs
 */
import pg from "pg"

const SLUG = "__test-concurrency"
let pass = 0, fail = 0
const ok = (m) => { console.log(`  PASS  ${m}`); pass++ }
const bad = (m, d) => { console.log(`  FAIL  ${m}${d ? ` — ${d}` : ""}`); fail++ }

const conn = () => new pg.Client({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
})

const a = conn(), b = conn()
await a.connect(); await b.connect()

async function cleanup() {
  await a.query(
    `DELETE FROM store_orders WHERE id IN (
       SELECT DISTINCT i.order_id FROM store_order_items i
        JOIN store_variants v ON v.id = i.variant_id
        JOIN store_products p ON p.id = v.product_id WHERE p.slug = $1)`, [SLUG])
  await a.query(`DELETE FROM store_products WHERE slug = $1`, [SLUG])
}
await cleanup()

// ── Fixture ─────────────────────────────────────────────────────────────────
const { rows: [prod] } = await a.query(
  `INSERT INTO store_products (slug, title, is_active) VALUES ($1, 'Concurrency Test', TRUE) RETURNING id`,
  [SLUG])
const { rows: [printV] } = await a.query(
  `INSERT INTO store_variants (product_id, kind, label, price_bdt, stock_qty, allow_cod)
   VALUES ($1,'print','Printed',600,1,TRUE) RETURNING id`, [prod.id])
const { rows: [digitalV] } = await a.query(
  `INSERT INTO store_variants (product_id, kind, label, price_bdt, stock_qty, allow_cod)
   VALUES ($1,'digital','PDF',600,NULL,FALSE) RETURNING id`, [prod.id])
const { rows: [dist] } = await a.query(`SELECT id FROM store_districts WHERE name = 'Dhaka'`)

// An account is required, so every order needs a real owner. Borrow any
// existing user rather than inventing one — auth.users has a foreign key.
const { rows: [someUser] } = await a.query(`SELECT id FROM auth.users LIMIT 1`)
if (!someUser) {
  console.log("\n  No user exists in auth.users, so the account requirement cannot be exercised.")
  console.log("  Sign up once in the app and re-run this script.\n")
  await cleanup(); await a.end(); await b.end()
  process.exit(1)
}
const USER = someUser.id

/**
 * Place an order through the real function.
 * `opts` lets a test omit a field deliberately to prove it is required.
 */
function createOrder(client, orderNumber, items, opts = {}) {
  const {
    userId = USER,
    method = "bkash",
    districtId = dist.id,
    email = "test@example.com",
    houseNo = "12",
    address = "House 12, Road 5, Dhanmondi, Dhaka",
  } = opts
  return client.query(
    `SELECT store_create_order(
       $1, $2, 'Test Buyer', '01712345678', $3,
       $4, 'Dhaka', 'Dhanmondi', $5, NULL, NULL,
       $6, '/store', NULL, $7::jsonb,
       $8, '5', NULL, NULL) AS r`,
    [orderNumber, userId, email, districtId, address, method, JSON.stringify(items), houseNo])
}

console.log("\nAn account is required")
{
  try {
    await createOrder(a, "GM-NOUSER", [{ variant_id: printV.id, quantity: 1 }], { userId: null })
    bad("an order with no account", "it was ACCEPTED")
  } catch (e) {
    /account is required/i.test(e.message)
      ? ok("an order with no account is refused")
      : bad("wrong error for a missing account", e.message)
  }

  try {
    await createOrder(a, "GM-NOEMAIL", [{ variant_id: printV.id, quantity: 1 }], { email: null })
    bad("an order with no email", "it was ACCEPTED")
  } catch (e) {
    /email/i.test(e.message) ? ok("an order with no email is refused") : bad("email check", e.message)
  }

  try {
    await createOrder(a, "GM-NOHOUSE", [{ variant_id: printV.id, quantity: 1 }], { houseNo: null })
    bad("an order with no house number", "it was ACCEPTED")
  } catch (e) {
    /house number/i.test(e.message)
      ? ok("an order with no house number is refused")
      : bad("house number check", e.message)
  }
}

console.log("\nDigital variants cannot be ordered while downloads are off")
{
  try {
    await a.query(
      `SELECT store_create_order('GM-DIGI-OFF', $1, 'T', '01712345678', 't@e.com',
         NULL,NULL,NULL,NULL,NULL,NULL,'bkash','/s',NULL,$2::jsonb,NULL,NULL,NULL,NULL)`,
      [USER, JSON.stringify([{ variant_id: digitalV.id, quantity: 1 }])])
    bad("a digital order", "it was ACCEPTED while downloads are off")
  } catch (e) {
    /not on sale/i.test(e.message)
      ? ok("a digital order is refused")
      : bad("digital block", e.message)
  }
}

console.log("\nTwo buyers race for the last copy")
{
  const items = [{ variant_id: printV.id, quantity: 1 }]
  const results = await Promise.allSettled([
    createOrder(a, "GM-RACE-A", items),
    createOrder(b, "GM-RACE-B", items),
  ])
  const won = results.filter(r => r.status === "fulfilled").length
  const lost = results.filter(r => r.status === "rejected").length

  won === 1 && lost === 1
    ? ok("exactly one order succeeded, the other was refused")
    : bad("stock race", `${won} succeeded, ${lost} refused — expected 1 and 1`)

  const loser = results.find(r => r.status === "rejected")
  if (loser && /out of stock/i.test(loser.reason.message)) ok("the loser got an out-of-stock error")
  else if (loser) bad("wrong error for the loser", loser.reason.message)

  const { rows: [s] } = await a.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [printV.id])
  s.stock_qty === 0 ? ok("stock is 0, never negative") : bad("stock", s.stock_qty)
}

console.log("\nTotals are computed by the database, not the caller")
{
  await a.query(`UPDATE store_variants SET stock_qty = 20 WHERE id = $1`, [printV.id])
  const { rows: [{ r }] } = await createOrder(a, "GM-TOTAL-1", [{ variant_id: printV.id, quantity: 2 }])
  r.subtotal_bdt === 1200 ? ok("subtotal 2 x 600 = 1200") : bad("subtotal", r.subtotal_bdt)
  r.delivery_bdt === 70 ? ok("Dhaka delivery = 70") : bad("delivery", r.delivery_bdt)
  r.total_bdt === 1270 ? ok("total = 1270") : bad("total", r.total_bdt)
  r.has_print === true && r.has_digital === false ? ok("flagged as a print order") : bad("flags", JSON.stringify(r))
}

console.log("\nThe per-title quantity cap holds, however it is split")
{
  try {
    await createOrder(a, "GM-CAP-1", [{ variant_id: printV.id, quantity: 11 }])
    bad("11 copies", "it was ACCEPTED")
  } catch (e) { /at most/i.test(e.message) ? ok("11 copies is refused") : bad("cap", e.message) }

  try {
    await createOrder(a, "GM-CAP-2", [
      { variant_id: printV.id, quantity: 6 },
      { variant_id: printV.id, quantity: 6 },
    ])
    bad("6 + 6 split across two lines", "it was ACCEPTED")
  } catch (e) {
    /at most/i.test(e.message) ? ok("6 + 6 split is refused") : bad("split cap", e.message)
  }
}

console.log("\nBusiness rules are refused at the database")
{
  const tryFail = async (label, fn, expect) => {
    try { await fn(); bad(label, "it was ACCEPTED") }
    catch (e) { expect.test(e.message) ? ok(label) : bad(label, e.message) }
  }

  await tryFail("a print order with no address is refused",
    () => createOrder(a, "GM-BAD-ADDR", [{ variant_id: printV.id, quantity: 1 }],
      { districtId: null, address: null }),
    /delivery address/i)

  await a.query(`UPDATE store_products SET is_active = FALSE WHERE id = $1`, [prod.id])
  await tryFail("an inactive product cannot be ordered",
    () => createOrder(a, "GM-BAD-INACTIVE", [{ variant_id: printV.id, quantity: 1 }]),
    /not on sale/i)
  await a.query(`UPDATE store_products SET is_active = TRUE WHERE id = $1`, [prod.id])
}

console.log("\nA failed order reserves no stock")
{
  const { rows: [before] } = await a.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [printV.id])
  try {
    await createOrder(a, "GM-ROLLBACK", [
      { variant_id: printV.id, quantity: 1 },
      { variant_id: "00000000-0000-0000-0000-000000000000", quantity: 1 },
    ])
    bad("an order with an unknown variant", "it was ACCEPTED")
  } catch { ok("an order with an unknown variant is refused") }
  const { rows: [after] } = await a.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [printV.id])
  after.stock_qty === before.stock_qty
    ? ok("the good line's stock was rolled back with the bad one")
    : bad("stock leaked on rollback", `${before.stock_qty} -> ${after.stock_qty}`)
}

console.log("\nVerifying a payment twice acts once")
{
  const { rows: [{ r }] } = await createOrder(a, "GM-VERIFY-1", [{ variant_id: printV.id, quantity: 1 }])
  const orderId = r.order_id
  await a.query(
    `INSERT INTO store_payments (order_id, method, transaction_id, amount_bdt)
     VALUES ($1,'bkash','TESTTRX01',670)`, [orderId])
  await a.query(`UPDATE store_orders SET payment_status = 'submitted' WHERE id = $1`, [orderId])

  const { rows: [v1] } = await a.query(`SELECT store_verify_payment($1,NULL,'admin@test','ok') AS r`, [orderId])
  const { rows: [v2] } = await a.query(`SELECT store_verify_payment($1,NULL,'admin@test','ok') AS r`, [orderId])

  v1.r.changed === true ? ok("the first verify changed the order") : bad("first verify", JSON.stringify(v1.r))
  v2.r.changed === false ? ok("the second verify was a no-op") : bad("second verify", JSON.stringify(v2.r))

  const { rows: [o] } = await a.query(
    `SELECT payment_status, order_status FROM store_orders WHERE id = $1`, [orderId])
  o.payment_status === "verified" && o.order_status === "confirmed"
    ? ok("order is verified and confirmed")
    : bad("order state", JSON.stringify(o))

  const { rows: [ev] } = await a.query(
    `SELECT count(*)::int n FROM store_order_events WHERE order_id = $1 AND field = 'payment_status'`, [orderId])
  ev.n === 1 ? ok("exactly one audit event was written") : bad("audit events", ev.n)
}

console.log("\nRejecting a payment lets the buyer try again")
{
  const { rows: [{ r }] } = await createOrder(a, "GM-REJECT-1", [{ variant_id: printV.id, quantity: 1 }])
  const orderId = r.order_id
  await a.query(
    `INSERT INTO store_payments (order_id, method, transaction_id) VALUES ($1,'bkash','TESTTRX02')`, [orderId])
  await a.query(`UPDATE store_orders SET payment_status = 'submitted' WHERE id = $1`, [orderId])

  const { rows: [{ r: rj }] } = await a.query(
    `SELECT store_reject_payment($1,NULL,'admin@test','wrong amount') AS r`, [orderId])
  rj.changed === true && rj.payment_status === "awaiting_payment"
    ? ok("the order returned to awaiting_payment")
    : bad("reject", JSON.stringify(rj))

  try {
    await a.query(
      `INSERT INTO store_payments (order_id, method, transaction_id) VALUES ($1,'bkash','TESTTRX02')`, [orderId])
    ok("the same Transaction ID can be resubmitted after rejection")
  } catch (e) { bad("resubmit after rejection", e.message) }
}

console.log("\nCash on delivery is accepted for a printed order")
{
  const { rows: [{ r }] } = await createOrder(
    a, "GM-COD-1", [{ variant_id: printV.id, quantity: 1 }], { method: "cod" })
  r.payment_status === "cod_pending"
    ? ok("the order waits for the courier to collect")
    : bad("cod payment status", r.payment_status)
}

console.log("\nCancelling gives the stock back, exactly once")
{
  await a.query(`UPDATE store_variants SET stock_qty = 10 WHERE id = $1`, [printV.id])
  const { rows: [before] } = await a.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [printV.id])
  const { rows: [{ r }] } = await createOrder(a, "GM-CANCEL-1", [{ variant_id: printV.id, quantity: 2 }])
  const { rows: [mid] } = await a.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [printV.id])
  mid.stock_qty === before.stock_qty - 2 ? ok("2 copies reserved") : bad("reserve", `${before.stock_qty} -> ${mid.stock_qty}`)

  await a.query(`SELECT store_cancel_order($1,NULL,'admin@test','test') AS r`, [r.order_id])
  await a.query(`SELECT store_cancel_order($1,NULL,'admin@test','test') AS r`, [r.order_id])

  const { rows: [after] } = await a.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [printV.id])
  after.stock_qty === before.stock_qty
    ? ok("stock restored once, not twice, despite a double cancel")
    : bad("restock", `expected ${before.stock_qty}, got ${after.stock_qty}`)
}

console.log("\nThe address is composed into one printable line")
{
  const { rows: [{ r }] } = await createOrder(a, "GM-ADDR-1", [{ variant_id: printV.id, quantity: 1 }])
  const { rows: [o] } = await a.query(
    `SELECT address_line, house_no, road_no, city, area FROM store_orders WHERE id = $1`, [r.order_id])
  o.house_no === "12" && o.road_no === "5" && o.city === "Dhaka" && o.area === "Dhanmondi"
    ? ok("the address parts are stored separately")
    : bad("address parts", JSON.stringify(o))
  typeof o.address_line === "string" && o.address_line.length > 10
    ? ok(`one printable line is kept ("${o.address_line}")`)
    : bad("address line", o.address_line)
}

console.log("\nOrder numbers are unique under a parallel burst")
{
  const { rows } = await a.query(
    `SELECT array_agg(store_next_order_seq()) AS seqs FROM generate_series(1,50)`)
  const seqs = rows[0].seqs
  new Set(seqs).size === 50 ? ok("50 sequence values, all distinct") : bad("sequence collisions", new Set(seqs).size)
}

await cleanup()
console.log("\n(test rows deleted)")
await a.end(); await b.end()
console.log(`\n${pass} passed, ${fail} failed\n`)
process.exit(fail ? 1 : 0)
