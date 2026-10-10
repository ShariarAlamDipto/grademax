/**
 * Phase-1 gate for the store schema.
 *
 * Proves the things that would silently sell a paid PDF to the public if they
 * were wrong: that the anon PostgREST surface cannot read any store table, that
 * the money/stock constraints actually reject bad rows, and that the partial
 * unique indexes behave the way the migration's comments claim.
 *
 *   node --env-file=.env.local scripts/verify-store-schema.mjs
 */
import pg from "pg"

const STORE_TABLES = [
  "store_districts", "store_settings", "store_products", "store_variants",
  "store_variant_files", "store_orders", "store_order_items", "store_payments",
  "store_order_events", "store_downloads", "store_rate_limits",
]

let pass = 0, fail = 0
const ok = (m) => { console.log(`  PASS  ${m}`); pass++ }
const bad = (m, d) => { console.log(`  FAIL  ${m}${d ? ` — ${d}` : ""}`); fail++ }

const client = new pg.Client({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
})
await client.connect()

/** Assert a statement is rejected by the database. */
async function mustReject(label, sql, params = []) {
  try {
    await client.query("SAVEPOINT sp")
    await client.query(sql, params)
    await client.query("ROLLBACK TO SAVEPOINT sp")
    bad(label, "the database ACCEPTED it")
  } catch {
    await client.query("ROLLBACK TO SAVEPOINT sp")
    ok(label)
  }
}

console.log("\nRLS is enabled on every store table")
{
  const { rows } = await client.query(
    `SELECT tablename, rowsecurity FROM pg_tables
      WHERE schemaname = 'public' AND tablename = ANY($1)`, [STORE_TABLES])
  const byName = Object.fromEntries(rows.map(r => [r.tablename, r.rowsecurity]))
  for (const t of STORE_TABLES) {
    if (byName[t] === undefined) bad(t, "table is missing")
    else if (byName[t]) ok(`${t} has RLS on`)
    else bad(t, "RLS is OFF — anon can read it")
  }
}

console.log("\nNo policy grants anon or authenticated any access")
{
  const { rows } = await client.query(
    `SELECT tablename, policyname, roles::text FROM pg_policies
      WHERE schemaname = 'public' AND tablename = ANY($1)`, [STORE_TABLES])
  const leaky = rows.filter(r => /anon|authenticated|\{public\}/.test(r.roles))
  // A {public} role entry is fine here only because every policy body requires
  // auth.role() = 'service_role'; check the body rather than trusting the role.
  const { rows: bodies } = await client.query(
    `SELECT tablename, policyname, qual FROM pg_policies
      WHERE schemaname = 'public' AND tablename = ANY($1)`, [STORE_TABLES])
  const permissive = bodies.filter(r => !/service_role/.test(r.qual ?? ""))
  if (permissive.length === 0) ok(`all ${bodies.length} policies require service_role`)
  else bad("a policy does not require service_role",
          permissive.map(p => `${p.tablename}.${p.policyname}`).join(", "))
  if (leaky.length && permissive.length === 0) ok("role grants are gated by the service_role predicate")
}

console.log("\nSeed data landed")
{
  const { rows: [d] } = await client.query("SELECT count(*)::int n FROM store_districts")
  d.n === 64 ? ok("64 districts") : bad("district count", `${d.n}, expected 64`)

  const { rows: prods } = await client.query(
    "SELECT slug, is_active FROM store_products ORDER BY sort_order")
  prods.length === 4 ? ok("4 products") : bad("product count", `${prods.length}, expected 4`)
  prods.every(p => p.is_active === false)
    ? ok("every product starts inactive — cannot sell an unuploaded file")
    : bad("a product is already active", prods.filter(p => p.is_active).map(p => p.slug).join(", "))

  const { rows: vars } = await client.query(
    `SELECT p.slug, v.kind, v.price_bdt FROM store_variants v
       JOIN store_products p ON p.id = v.product_id ORDER BY p.sort_order, v.kind`)
  vars.length === 8 ? ok("8 variants (print + digital each)") : bad("variant count", vars.length)

  const priced = Object.fromEntries(vars.map(v => [`${v.slug}:${v.kind}`, v.price_bdt]))
  const expect = {
    "mathematics-b-part-1:print": 600, "mathematics-b-part-2:print": 600,
    "further-pure-mathematics:print": 800,
  }
  for (const [k, want] of Object.entries(expect)) {
    priced[k] === want ? ok(`${k} = ${want} BDT`) : bad(k, `${priced[k]}, expected ${want}`)
  }
}

console.log("\nConstraints reject bad data")
await client.query("BEGIN")

await mustReject("negative stock is rejected",
  `UPDATE store_variants SET stock_qty = -1 WHERE kind = 'print'`)

await mustReject("negative price is rejected",
  `UPDATE store_variants SET price_bdt = -1 WHERE kind = 'print'`)

await mustReject("a digital variant cannot allow cash on delivery",
  `UPDATE store_variants SET allow_cod = TRUE WHERE kind = 'digital'`)

await mustReject("a digital variant cannot carry stock",
  `UPDATE store_variants SET stock_qty = 5 WHERE kind = 'digital'`)

// An order whose total does not equal subtotal + delivery - discount.
await mustReject("an order whose arithmetic is wrong is rejected",
  `INSERT INTO store_orders (order_number, customer_name, customer_phone,
     has_print, has_digital, subtotal_bdt, delivery_bdt, discount_bdt, total_bdt, payment_method)
   VALUES ('GM-TEST-BAD','T','01700000000', FALSE, TRUE, 600, 0, 0, 999, 'bkash')`)

await mustReject("a shipped order with no address is rejected",
  `INSERT INTO store_orders (order_number, customer_name, customer_phone,
     has_print, has_digital, subtotal_bdt, delivery_bdt, discount_bdt, total_bdt, payment_method)
   VALUES ('GM-TEST-NOADDR','T','01700000000', TRUE, FALSE, 600, 70, 0, 670, 'bkash')`)

await mustReject("cash on delivery with a digital item is rejected",
  `INSERT INTO store_orders (order_number, customer_name, customer_phone,
     has_print, has_digital, subtotal_bdt, delivery_bdt, discount_bdt, total_bdt, payment_method)
   VALUES ('GM-TEST-COD','T','01700000000', FALSE, TRUE, 600, 0, 0, 600, 'cod')`)

console.log("\nPayment uniqueness behaves as designed")
{
  const { rows: [o1] } = await client.query(
    `INSERT INTO store_orders (order_number, customer_name, customer_phone,
       has_print, has_digital, subtotal_bdt, delivery_bdt, discount_bdt, total_bdt, payment_method)
     VALUES ('GM-TEST-A','T','01700000000', FALSE, TRUE, 600, 0, 0, 600, 'bkash') RETURNING id`)
  const { rows: [o2] } = await client.query(
    `INSERT INTO store_orders (order_number, customer_name, customer_phone,
       has_print, has_digital, subtotal_bdt, delivery_bdt, discount_bdt, total_bdt, payment_method)
     VALUES ('GM-TEST-B','T','01700000001', FALSE, TRUE, 600, 0, 0, 600, 'bkash') RETURNING id`)

  await client.query(
    `INSERT INTO store_payments (order_id, method, transaction_id, amount_bdt)
     VALUES ($1,'bkash','  ab12cd34  ',600)`, [o1.id])
  ok("a payment claim can be submitted")

  await mustReject("the same TrxID cannot be claimed on another order (case/space-insensitive)",
    `INSERT INTO store_payments (order_id, method, transaction_id, amount_bdt)
     VALUES ($1,'bkash','AB12CD34',600)`, [o2.id])

  await mustReject("one order cannot carry two live payment claims",
    `INSERT INTO store_payments (order_id, method, transaction_id, amount_bdt)
     VALUES ($1,'bkash','ZZ99ZZ99',600)`, [o1.id])

  // Reject the first claim, then prove the SAME TrxID can be resubmitted —
  // this is the case a plain UNIQUE(method, transaction_id) would have burned.
  await client.query(
    `UPDATE store_payments SET status = 'rejected' WHERE order_id = $1`, [o1.id])
  try {
    await client.query(
      `INSERT INTO store_payments (order_id, method, transaction_id, amount_bdt)
       VALUES ($1,'bkash','AB12CD34',600)`, [o1.id])
    ok("a rejected TrxID can be resubmitted")
  } catch (e) {
    bad("a rejected TrxID could NOT be resubmitted", e.message)
  }
}

console.log("\nStock reservation is atomic")
{
  const { rows: [v] } = await client.query(
    `SELECT id FROM store_variants WHERE kind = 'print' LIMIT 1`)
  await client.query(`UPDATE store_variants SET stock_qty = 1 WHERE id = $1`, [v.id])

  const { rows: [a] } = await client.query(`SELECT store_reserve_stock($1, 1) AS okd`, [v.id])
  const { rows: [b] } = await client.query(`SELECT store_reserve_stock($1, 1) AS okd`, [v.id])
  a.okd === true && b.okd === false
    ? ok("the last copy is reserved once and the second attempt is refused")
    : bad("stock reservation", `first=${a.okd} second=${b.okd}, expected true then false`)

  const { rows: [s] } = await client.query(`SELECT stock_qty FROM store_variants WHERE id = $1`, [v.id])
  s.stock_qty === 0 ? ok("stock never went negative") : bad("stock", s.stock_qty)
}

await client.query("ROLLBACK")
console.log("\n(all test rows rolled back)")

await client.end()
console.log(`\n${pass} passed, ${fail} failed\n`)
process.exit(fail ? 1 : 0)
