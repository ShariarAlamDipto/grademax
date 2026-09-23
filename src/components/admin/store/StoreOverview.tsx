"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { formatBdt } from "@/lib/store/format"

/**
 * Store overview — money, work queues, and where the orders come from.
 *
 * Revenue counts verified and paid-on-delivery orders only. Counting payments
 * that are merely claimed would report income from Transaction IDs nobody has
 * checked yet, which is exactly the figure most likely to be wrong.
 */

interface Stats {
  days: number
  totals: {
    orders: number
    paidOrders: number
    revenueBdt: number
    awaitingVerification: number
    awaitingPayment: number
    toShip: number
    cancelled: number
  }
  byDistrict: { district: string; division: string; orders: number; revenueBdt: number }[]
  byDivision: { division: string; orders: number; revenueBdt: number }[]
  bySource: { path: string; orders: number }[]
  byDay: { day: string; orders: number; revenueBdt: number }[]
}

const RANGES = [7, 30, 90, 365]

export default function StoreOverview() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [days, setDays] = useState(30)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setStats(null)
    fetch(`/api/admin/store/stats?days=${days}`)
      .then(r => r.json())
      .then(d => {
        if (cancelled) return
        if (d.error) setError(d.error)
        else setStats(d)
      })
      .catch(() => { if (!cancelled) setError("Could not load store statistics.") })
    return () => { cancelled = true }
  }, [days])

  return (
    <div style={{ padding: "1.75rem", maxWidth: "76rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>Store</h1>
          <p style={{ fontSize: "0.82rem", color: "var(--gm-text-3)", marginTop: "0.25rem" }}>
            Orders, revenue and where your buyers are.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          {RANGES.map(r => (
            <button key={r} onClick={() => setDays(r)} style={{
              padding: "0.35rem 0.7rem", borderRadius: "0.45rem", cursor: "pointer",
              fontSize: "0.75rem", fontWeight: 600,
              background: days === r ? "var(--gm-amber-bg)" : "var(--gm-surface-2)",
              color: days === r ? "var(--gm-amber)" : "var(--gm-text-3)",
              border: `1px solid ${days === r ? "var(--gm-amber)" : "var(--gm-border-2)"}`,
            }}>
              {r === 365 ? "1 year" : `${r} days`}
            </button>
          ))}
        </div>
      </header>

      <nav style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <TabLink href="/admin/store/orders">Orders</TabLink>
        <TabLink href="/admin/store/products">Products &amp; prices</TabLink>
        <TabLink href="/store">View the shop →</TabLink>
      </nav>

      {error ? <Panel><p style={{ color: "#ef4444", fontSize: "0.85rem" }}>{error}</p></Panel> : null}
      {!stats && !error ? <Panel><p style={{ color: "var(--gm-text-3)", fontSize: "0.85rem" }}>Loading…</p></Panel> : null}

      {stats ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(10rem, 1fr))", gap: "0.75rem", marginBottom: "1.25rem" }}>
            <Stat label="Revenue" value={formatBdt(stats.totals.revenueBdt)} hint={`${stats.totals.paidOrders} paid orders`} tone="green" />
            <Stat label="Orders" value={String(stats.totals.orders)} hint={`${stats.totals.cancelled} cancelled`} />
            <Stat label="To verify" value={String(stats.totals.awaitingVerification)} hint="Payments claimed" tone={stats.totals.awaitingVerification > 0 ? "amber" : undefined} />
            <Stat label="To ship" value={String(stats.totals.toShip)} hint="Confirmed or packed" tone={stats.totals.toShip > 0 ? "blue" : undefined} />
            <Stat label="Unpaid" value={String(stats.totals.awaitingPayment)} hint="Awaiting payment" />
          </div>

          {stats.totals.awaitingVerification > 0 ? (
            <div style={{
              background: "var(--gm-amber-bg)", border: "1px solid var(--gm-amber)",
              borderRadius: "0.6rem", padding: "0.85rem 1rem", marginBottom: "1.25rem",
              display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap",
            }}>
              <span style={{ fontSize: "0.85rem" }}>
                <strong>{stats.totals.awaitingVerification}</strong> payment
                {stats.totals.awaitingVerification === 1 ? " is" : "s are"} waiting to be checked.
                Buyers are not served until you verify them.
              </span>
              <Link href="/admin/store/orders?payment_status=submitted" style={{
                background: "var(--gm-amber)", color: "#1a1206", padding: "0.4rem 0.8rem",
                borderRadius: "0.45rem", fontSize: "0.78rem", fontWeight: 700, textDecoration: "none",
              }}>
                Verify now
              </Link>
            </div>
          ) : null}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 22rem), 1fr))", gap: "1rem" }}>
            <Panel title="Where orders come from" subtitle="By district, most orders first">
              {stats.byDistrict.length === 0 ? (
                <Empty>No orders yet in this period.</Empty>
              ) : (
                <BarList
                  rows={stats.byDistrict.map(d => ({
                    label: d.district,
                    sub: d.division,
                    value: d.orders,
                    right: formatBdt(d.revenueBdt),
                  }))}
                />
              )}
            </Panel>

            <Panel title="By division" subtitle="Useful for planning courier runs">
              {stats.byDivision.length === 0 ? (
                <Empty>No orders yet.</Empty>
              ) : (
                <BarList
                  rows={stats.byDivision.map(d => ({
                    label: d.division,
                    value: d.orders,
                    right: formatBdt(d.revenueBdt),
                  }))}
                />
              )}
            </Panel>

            <Panel title="Which page they came from" subtitle="The page the buyer was on before checkout">
              {stats.bySource.length === 0 ? (
                <Empty>No orders yet.</Empty>
              ) : (
                <BarList rows={stats.bySource.map(s => ({ label: s.path, value: s.orders }))} />
              )}
            </Panel>

            <Panel title="Orders per day" subtitle="Dhaka time">
              {stats.byDay.length === 0 ? (
                <Empty>No orders yet.</Empty>
              ) : (
                <DayChart rows={stats.byDay} />
              )}
            </Panel>
          </div>
        </>
      ) : null}
    </div>
  )
}

function TabLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} style={{
      padding: "0.4rem 0.8rem", borderRadius: "0.45rem",
      background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)",
      fontSize: "0.78rem", fontWeight: 600, color: "var(--gm-text-2)", textDecoration: "none",
    }}>
      {children}
    </Link>
  )
}

function Stat({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "green" | "amber" | "blue" }) {
  const colors = { green: "var(--gm-green)", amber: "var(--gm-amber)", blue: "var(--gm-blue)" }
  return (
    <div style={{ background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.65rem", padding: "0.9rem" }}>
      <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gm-text-3)" }}>
        {label}
      </span>
      <strong style={{ display: "block", fontSize: "1.4rem", fontWeight: 800, marginTop: "0.3rem", color: tone ? colors[tone] : "var(--gm-text)" }}>
        {value}
      </strong>
      {hint ? <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>{hint}</span> : null}
    </div>
  )
}

function Panel({ title, subtitle, children }: { title?: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section style={{ background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.65rem", padding: "1rem" }}>
      {title ? (
        <header style={{ marginBottom: "0.85rem" }}>
          <h2 style={{ fontSize: "0.85rem", fontWeight: 700 }}>{title}</h2>
          {subtitle ? <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.15rem" }}>{subtitle}</p> : null}
        </header>
      ) : null}
      {children}
    </section>
  )
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", padding: "1rem 0", textAlign: "center" }}>{children}</p>
}

function BarList({ rows }: { rows: { label: string; sub?: string; value: number; right?: string }[] }) {
  const max = Math.max(...rows.map(r => r.value), 1)
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", maxHeight: "22rem", overflowY: "auto" }}>
      {rows.map((r, i) => (
        <div key={i}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", marginBottom: "0.2rem" }}>
            <span style={{ fontSize: "0.78rem", fontWeight: 600, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.label}
              {r.sub ? <span style={{ color: "var(--gm-text-3)", fontWeight: 400 }}> · {r.sub}</span> : null}
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", whiteSpace: "nowrap" }}>
              {r.right ? `${r.right} · ` : ""}{r.value}
            </span>
          </div>
          <div style={{ height: "4px", borderRadius: "2px", background: "var(--gm-surface-2)" }}>
            <div style={{ width: `${(r.value / max) * 100}%`, height: "100%", borderRadius: "2px", background: "var(--gm-blue)" }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function DayChart({ rows }: { rows: { day: string; orders: number; revenueBdt: number }[] }) {
  const max = Math.max(...rows.map(r => r.orders), 1)
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: "2px", height: "8rem" }}>
      {rows.map(r => (
        <div key={r.day} title={`${r.day} · ${r.orders} orders · ${formatBdt(r.revenueBdt)}`}
             style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", justifyContent: "flex-end", height: "100%" }}>
          <div style={{
            height: `${Math.max((r.orders / max) * 100, 3)}%`,
            background: "var(--gm-amber)", borderRadius: "2px 2px 0 0",
          }} />
        </div>
      ))}
    </div>
  )
}
