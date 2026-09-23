import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * GET /api/admin/store/stats — the "where are orders coming from" view.
 *
 * Revenue counts only money that actually arrived: verified payments and orders
 * paid on delivery. Counting `submitted` would report income from Transaction
 * IDs nobody has checked yet, which is the number most likely to be believed
 * and most likely to be wrong.
 *
 * Days are bucketed in Asia/Dhaka, not UTC — an order placed at 9pm Dhaka time
 * would otherwise land on the following day.
 */
export const dynamic = "force-dynamic"

const PAID_STATES = ["verified", "paid_on_delivery"]

interface OrderRow {
  total_bdt: number
  payment_status: string
  order_status: string
  has_print: boolean
  has_digital: boolean
  created_at: string
  district_id: number | null
  source_path: string | null
  source_referrer: string | null
  store_districts: { name: string; division: string; is_metro: boolean } | null
}

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Unavailable" }, { status: 503 })

  const days = Math.min(Math.max(Number(new URL(req.url).searchParams.get("days")) || 30, 1), 365)
  const since = new Date(Date.now() - days * 86_400_000).toISOString()

  const { data, error } = await db
    .from("store_orders")
    .select("total_bdt, payment_status, order_status, has_print, has_digital, created_at, district_id, source_path, source_referrer, store_districts(name, division, is_metro)")
    .gte("created_at", since)
    .limit(5000)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  const orders = (data ?? []) as unknown as OrderRow[]
  const live = orders.filter(o => o.order_status !== "cancelled")
  const paid = live.filter(o => PAID_STATES.includes(o.payment_status))

  // ── Where orders come from, by district ──
  const byDistrict = new Map<string, { district: string; division: string; orders: number; revenueBdt: number }>()
  for (const o of live) {
    const name = o.store_districts?.name ?? "Digital — no address"
    const division = o.store_districts?.division ?? "—"
    const row = byDistrict.get(name) ?? { district: name, division, orders: 0, revenueBdt: 0 }
    row.orders += 1
    if (PAID_STATES.includes(o.payment_status)) row.revenueBdt += o.total_bdt
    byDistrict.set(name, row)
  }

  const byDivision = new Map<string, { division: string; orders: number; revenueBdt: number }>()
  for (const row of byDistrict.values()) {
    const d = byDivision.get(row.division) ?? { division: row.division, orders: 0, revenueBdt: 0 }
    d.orders += row.orders
    d.revenueBdt += row.revenueBdt
    byDivision.set(row.division, d)
  }

  // ── Which page the buyer came from ──
  const bySource = new Map<string, number>()
  for (const o of live) {
    const key = o.source_path || "direct"
    bySource.set(key, (bySource.get(key) ?? 0) + 1)
  }

  // ── Orders per day, in Dhaka time ──
  const byDay = new Map<string, { day: string; orders: number; revenueBdt: number }>()
  for (const o of live) {
    const day = new Date(o.created_at).toLocaleDateString("en-CA", { timeZone: "Asia/Dhaka" })
    const row = byDay.get(day) ?? { day, orders: 0, revenueBdt: 0 }
    row.orders += 1
    if (PAID_STATES.includes(o.payment_status)) row.revenueBdt += o.total_bdt
    byDay.set(day, row)
  }

  const counts = (field: keyof OrderRow) => {
    const m: Record<string, number> = {}
    for (const o of live) {
      const k = String(o[field])
      m[k] = (m[k] ?? 0) + 1
    }
    return m
  }

  return NextResponse.json({
    days,
    totals: {
      orders: live.length,
      paidOrders: paid.length,
      revenueBdt: paid.reduce((s, o) => s + o.total_bdt, 0),
      awaitingVerification: live.filter(o => o.payment_status === "submitted").length,
      awaitingPayment: live.filter(o => o.payment_status === "awaiting_payment").length,
      toShip: live.filter(o => o.has_print && ["confirmed", "packed"].includes(o.order_status)).length,
      cancelled: orders.length - live.length,
    },
    byDistrict: [...byDistrict.values()].sort((a, b) => b.orders - a.orders),
    byDivision: [...byDivision.values()].sort((a, b) => b.orders - a.orders),
    bySource: [...bySource.entries()].map(([path, orders]) => ({ path, orders })).sort((a, b) => b.orders - a.orders).slice(0, 20),
    byDay: [...byDay.values()].sort((a, b) => a.day.localeCompare(b.day)),
    paymentStatus: counts("payment_status"),
    orderStatus: counts("order_status"),
  })
}
