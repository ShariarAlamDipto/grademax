"use client"

import Link from "next/link"
import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { formatBdt, formatDhakaDate, formatPhone } from "@/lib/store/format"
import { ORDER_STATUS_LABEL, PAYMENT_STATUS_LABEL, type OrderStatus, type PaymentStatus } from "@/lib/store/types"

/**
 * The order queue and the payment verification screen.
 *
 * Verifying is the action that releases a digital file and commits to shipping
 * a book, so the buyer's claim is shown in full next to the order total — the
 * amount they say they sent, the number they sent it from, and the Transaction
 * ID to check against the bKash or Nagad app. A mismatch is called out rather
 * than left for the eye to catch.
 */

interface Payment {
  id: string
  method: string
  sender_msisdn: string | null
  transaction_id: string | null
  amount_bdt: number | null
  status: string
  rejection_reason: string | null
  created_at: string
}

interface Order {
  id: string
  order_number: string
  customer_name: string
  customer_phone: string
  customer_email: string | null
  city: string | null
  area: string | null
  address_line: string | null
  house_no: string | null
  road_no: string | null
  landmark: string | null
  alt_phone: string | null
  postcode: string | null
  has_print: boolean
  has_digital: boolean
  subtotal_bdt: number
  delivery_bdt: number
  total_bdt: number
  payment_method: string
  payment_status: PaymentStatus
  order_status: OrderStatus
  courier_name: string | null
  tracking_code: string | null
  source_path: string | null
  admin_note: string | null
  created_at: string
  store_districts: { id: number; name: string; division: string } | null
  store_order_items: { id: string; product_title: string; variant_label: string; variant_kind: string; quantity: number; line_total_bdt: number }[]
  store_payments: Payment[]
}

const PAYMENT_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All payments" },
  { value: "submitted", label: "To verify" },
  { value: "awaiting_payment", label: "Unpaid" },
  { value: "verified", label: "Verified" },
  { value: "cod_pending", label: "Cash on delivery" },
  { value: "rejected", label: "Rejected" },
]

const ORDER_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "packed", label: "Packed" },
  { value: "shipped", label: "Shipped" },
  { value: "delivered", label: "Delivered" },
  { value: "cancelled", label: "Cancelled" },
]

export default function StoreOrders() {
  const params = useSearchParams()
  const [orders, setOrders] = useState<Order[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [paymentStatus, setPaymentStatus] = useState(params.get("payment_status") ?? "")
  const [orderStatus, setOrderStatus] = useState("")
  const [search, setSearch] = useState("")
  // `search` feeds `load`, so without this every keystroke would fire a request.
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [selected, setSelected] = useState<Order | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams()
      if (paymentStatus) qs.set("payment_status", paymentStatus)
      if (orderStatus) qs.set("order_status", orderStatus)
      if (debouncedSearch.trim()) qs.set("q", debouncedSearch.trim())
      const res = await fetch(`/api/admin/store/orders?${qs}`)
      const json = await res.json()
      if (!res.ok) { setError(json.error ?? "Could not load orders."); return }
      setOrders(json.orders ?? [])
      setTotal(json.total ?? 0)
      // Keep the open order in step with the refreshed list.
      setSelected(prev => prev ? (json.orders ?? []).find((o: Order) => o.id === prev.id) ?? null : null)
    } catch {
      setError("Could not load orders.")
    } finally {
      setLoading(false)
    }
  }, [paymentStatus, orderStatus, debouncedSearch])

  useEffect(() => { void load() }, [load])

  return (
    <div style={{ padding: "1.75rem", maxWidth: "84rem" }}>
      <header style={{ marginBottom: "1.25rem" }}>
        <Link href="/admin/store" style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", textDecoration: "none" }}>
          ← Store overview
        </Link>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em", marginTop: "0.35rem" }}>
          Orders {total > 0 ? <span style={{ color: "var(--gm-text-3)", fontWeight: 400, fontSize: "1rem" }}>({total})</span> : null}
        </h1>
      </header>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <select className="gm-select" value={paymentStatus} onChange={e => setPaymentStatus(e.target.value)} style={{ maxWidth: "12rem" }}>
          {PAYMENT_FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
        <select className="gm-select" value={orderStatus} onChange={e => setOrderStatus(e.target.value)} style={{ maxWidth: "12rem" }}>
          {ORDER_FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
        <input className="gm-input" value={search} onChange={e => setSearch(e.target.value)}
               placeholder="Order number, name or phone" style={{ maxWidth: "18rem" }} />
        <button onClick={() => void load()} style={btn("secondary")}>Refresh</button>
      </div>

      {error ? <p style={{ color: "#ef4444", fontSize: "0.85rem" }}>{error}</p> : null}
      {loading ? <p style={{ color: "var(--gm-text-3)", fontSize: "0.85rem" }}>Loading…</p> : null}

      {!loading && orders.length === 0 ? (
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.85rem", padding: "2rem 0" }}>
          No orders match this filter.
        </p>
      ) : null}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {orders.map(order => (
          <OrderRow key={order.id} order={order} onOpen={() => setSelected(order)} />
        ))}
      </div>

      {selected ? (
        <OrderDrawer order={selected} onClose={() => setSelected(null)} onChanged={load} />
      ) : null}
    </div>
  )
}

function tone(status: PaymentStatus): { bg: string; fg: string } {
  if (status === "verified" || status === "paid_on_delivery") return { bg: "var(--gm-green-bg)", fg: "var(--gm-green)" }
  if (status === "submitted") return { bg: "var(--gm-amber-bg)", fg: "var(--gm-amber)" }
  if (status === "rejected" || status === "refunded") return { bg: "#ef444422", fg: "#ef4444" }
  return { bg: "var(--gm-surface-2)", fg: "var(--gm-text-3)" }
}

function OrderRow({ order, onOpen }: { order: Order; onOpen: () => void }) {
  const t = tone(order.payment_status)
  return (
    <button onClick={onOpen} style={{
      display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr) auto auto",
      gap: "0.9rem", alignItems: "center", width: "100%", textAlign: "left", cursor: "pointer",
      background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)",
      borderRadius: "0.55rem", padding: "0.75rem 0.9rem", color: "var(--gm-text)",
    }}>
      <span style={{ minWidth: 0 }}>
        <strong style={{ fontSize: "0.85rem", fontWeight: 700, display: "block" }}>{order.order_number}</strong>
        <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)" }}>
          {order.customer_name} · {formatPhone(order.customer_phone)}
        </span>
      </span>

      <span style={{ minWidth: 0, fontSize: "0.75rem", color: "var(--gm-text-3)" }}>
        {order.store_districts?.name ?? (order.has_digital ? "Digital" : "—")}
        <span style={{ display: "block" }}>{formatDhakaDate(order.created_at)}</span>
      </span>

      <span style={{
        background: t.bg, color: t.fg, borderRadius: "0.35rem", padding: "0.15rem 0.5rem",
        fontSize: "0.68rem", fontWeight: 700, whiteSpace: "nowrap",
      }}>
        {PAYMENT_STATUS_LABEL[order.payment_status]}
      </span>

      <strong style={{ fontSize: "0.9rem", whiteSpace: "nowrap" }}>{formatBdt(order.total_bdt)}</strong>
    </button>
  )
}

function OrderDrawer({ order, onClose, onChanged }: { order: Order; onClose: () => void; onChanged: () => void }) {
  const [busy, setBusy] = useState(false)

  // Escape closes the drawer, which is what every other modal on the web does.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const [message, setMessage] = useState<string | null>(null)
  const [reason, setReason] = useState("")
  const [courier, setCourier] = useState(order.courier_name ?? "")
  const [tracking, setTracking] = useState(order.tracking_code ?? "")

  const claim = order.store_payments?.find(p => p.status === "submitted")
    ?? order.store_payments?.find(p => p.status === "verified")
    ?? null

  const amountMismatch = claim?.amount_bdt != null && claim.amount_bdt !== order.total_bdt

  async function decide(decision: "verify" | "reject") {
    if (decision === "reject" && reason.trim().length < 3) {
      setMessage("Give a reason — the buyer sees it and needs to know what to fix.")
      return
    }
    setBusy(true)
    setMessage(null)
    try {
      const res = await fetch("/api/admin/store/payment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ orderId: order.id, decision, reason: reason.trim() || undefined }),
      })
      const json = await res.json()
      setMessage(json.error ?? json.message ?? null)
      if (res.ok) onChanged()
    } catch {
      setMessage("The request failed.")
    } finally {
      setBusy(false)
    }
  }

  async function updateOrder(patch: Record<string, unknown>) {
    setBusy(true)
    setMessage(null)
    try {
      const res = await fetch("/api/admin/store/orders", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ orderId: order.id, ...patch }),
      })
      const json = await res.json()
      setMessage(json.error ?? "Saved.")
      if (res.ok) onChanged()
    } catch {
      setMessage("The request failed.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div onClick={onClose} aria-hidden="true"
           style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 400 }} />
      <aside role="dialog" aria-modal="true" aria-label={`Order ${order.order_number}`} style={{
        position: "fixed", top: 0, right: 0, bottom: 0, width: "min(32rem, 100vw)", zIndex: 401,
        background: "var(--gm-surface)", borderLeft: "1px solid var(--gm-border)",
        overflowY: "auto", padding: "1.5rem",
      }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
          <div>
            <strong style={{ fontSize: "1.05rem", fontWeight: 800 }}>{order.order_number}</strong>
            <span style={{ display: "block", fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>
              {formatDhakaDate(order.created_at)}
            </span>
          </div>
          <button onClick={onClose} aria-label="Close order details"
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--gm-text-3)", fontSize: "1.2rem", lineHeight: 1 }}>
            ×
          </button>
        </header>

        {message ? (
          <div style={{
            background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)",
            borderRadius: "0.5rem", padding: "0.6rem 0.75rem", fontSize: "0.8rem", marginBottom: "1rem",
          }}>
            {message}
          </div>
        ) : null}

        <Section title="Customer">
          <Line label="Name" value={order.customer_name} />
          <Line label="Phone" value={formatPhone(order.customer_phone)} />
          {order.customer_email ? <Line label="Email" value={order.customer_email} /> : null}
          {order.alt_phone ? <Line label="Other phone" value={formatPhone(order.alt_phone)} /> : null}
          {order.has_print ? (
            <>
              <Line label="District" value={order.store_districts?.name ?? "—"} />
              <Line label="City" value={order.city ?? "—"} />
              <Line label="Area" value={order.area ?? "—"} />
              <Line label="House" value={order.house_no ?? "—"} />
              {order.road_no ? <Line label="Road" value={order.road_no} /> : null}
              {order.landmark ? <Line label="Landmark" value={order.landmark} /> : null}
              {order.postcode ? <Line label="Postcode" value={order.postcode} /> : null}
              {/* The one line to copy onto a delivery label. */}
              <div style={{ marginTop: "0.5rem", padding: "0.6rem", borderRadius: "0.45rem",
                            background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)" }}>
                <span style={{ fontSize: "0.65rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.2rem" }}>
                  For the delivery label
                </span>
                <span style={{ fontSize: "0.78rem", lineHeight: 1.5 }}>{order.address_line ?? "—"}</span>
              </div>
            </>
          ) : (
            <Line label="Delivery" value="Digital only — nothing to ship" />
          )}
          {order.source_path ? <Line label="Came from" value={order.source_path} /> : null}
        </Section>

        <Section title="Items">
          {order.store_order_items.map(item => (
            <div key={item.id} style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", fontSize: "0.8rem", marginBottom: "0.4rem" }}>
              <span>
                {item.product_title}
                <span style={{ color: "var(--gm-text-3)" }}> · {item.variant_kind === "print" ? "Printed" : "PDF"} × {item.quantity}</span>
              </span>
              <strong style={{ whiteSpace: "nowrap" }}>{formatBdt(item.line_total_bdt)}</strong>
            </div>
          ))}
          <div style={{ borderTop: "1px solid var(--gm-border)", marginTop: "0.6rem", paddingTop: "0.6rem" }}>
            <Line label="Subtotal" value={formatBdt(order.subtotal_bdt)} />
            <Line label="Delivery" value={formatBdt(order.delivery_bdt)} />
            <Line label="Total" value={formatBdt(order.total_bdt)} strong />
          </div>
        </Section>

        <Section title="Payment">
          <Line label="Method" value={order.payment_method.toUpperCase()} />
          <Line label="Status" value={PAYMENT_STATUS_LABEL[order.payment_status]} />

          {claim ? (
            <div style={{
              background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)",
              borderRadius: "0.5rem", padding: "0.75rem", margin: "0.75rem 0",
            }}>
              <Line label="Transaction ID" value={claim.transaction_id ?? "—"} strong />
              <Line label="Sent from" value={claim.sender_msisdn ? formatPhone(claim.sender_msisdn) : "—"} />
              <Line label="Amount claimed" value={claim.amount_bdt != null ? formatBdt(claim.amount_bdt) : "—"} />
              <Line label="Claimed at" value={formatDhakaDate(claim.created_at)} />
              {amountMismatch ? (
                <p style={{ color: "#ef4444", fontSize: "0.75rem", marginTop: "0.5rem", lineHeight: 1.5 }}>
                  This does not match the order total of {formatBdt(order.total_bdt)}. Check the
                  app before verifying.
                </p>
              ) : null}
            </div>
          ) : (
            <p style={{ fontSize: "0.78rem", color: "var(--gm-text-3)", margin: "0.5rem 0" }}>
              No payment has been claimed yet.
            </p>
          )}

          {order.payment_status === "submitted" ? (
            <>
              <textarea className="gm-input" rows={2} value={reason} onChange={e => setReason(e.target.value)}
                        placeholder="Note, or reason if you reject" style={{ resize: "vertical", marginBottom: "0.6rem" }} />
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <button disabled={busy} onClick={() => decide("verify")} style={btn("primary")}>
                  {busy ? "Working…" : "Verify payment"}
                </button>
                <button disabled={busy} onClick={() => decide("reject")} style={btn("danger")}>
                  Reject
                </button>
              </div>
            </>
          ) : null}
        </Section>

        {order.has_print ? (
          <Section title="Fulfilment">
            <Line label="Status" value={ORDER_STATUS_LABEL[order.order_status]} />
            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", margin: "0.7rem 0" }}>
              {(["confirmed", "packed", "shipped", "delivered"] as OrderStatus[]).map(s => (
                <button key={s} disabled={busy || order.order_status === s}
                        onClick={() => updateOrder({ orderStatus: s })}
                        style={btn(order.order_status === s ? "ghost" : "secondary")}>
                  {ORDER_STATUS_LABEL[s]}
                </button>
              ))}
            </div>
            <input className="gm-input" value={courier} onChange={e => setCourier(e.target.value)}
                   placeholder="Courier (e.g. Pathao, Steadfast)" style={{ marginBottom: "0.5rem" }} />
            <input className="gm-input" value={tracking} onChange={e => setTracking(e.target.value)}
                   placeholder="Tracking / consignment number" style={{ marginBottom: "0.6rem" }} />
            <button disabled={busy} onClick={() => updateOrder({ courierName: courier || null, trackingCode: tracking || null })}
                    style={btn("secondary")}>
              Save courier details
            </button>
          </Section>
        ) : null}

        {order.order_status !== "cancelled" ? (
          <Section title="Danger zone">
            <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.6rem", lineHeight: 1.55 }}>
              Cancelling returns any reserved copies to stock and revokes digital access.
            </p>
            <button disabled={busy} onClick={() => updateOrder({ orderStatus: "cancelled", adminNote: reason || "Cancelled by admin" })}
                    style={btn("danger")}>
              Cancel this order
            </button>
          </Section>
        ) : null}
      </aside>
    </>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: "1.5rem" }}>
      <h2 style={{
        fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
        color: "var(--gm-text-3)", marginBottom: "0.6rem",
      }}>
        {title}
      </h2>
      {children}
    </section>
  )
}

function Line({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", fontSize: "0.8rem", marginBottom: "0.3rem" }}>
      <span style={{ color: "var(--gm-text-3)", flexShrink: 0 }}>{label}</span>
      <span style={{ fontWeight: strong ? 700 : 500, textAlign: "right", minWidth: 0, wordBreak: "break-word" }}>{value}</span>
    </div>
  )
}

function btn(variant: "primary" | "secondary" | "ghost" | "danger"): React.CSSProperties {
  const palette = {
    primary:   { background: "var(--gm-amber)", color: "#1a1206", border: "1px solid transparent" },
    secondary: { background: "var(--gm-surface-2)", color: "var(--gm-text)", border: "1px solid var(--gm-border-2)" },
    ghost:     { background: "transparent", color: "var(--gm-text-3)", border: "1px solid var(--gm-border)" },
    danger:    { background: "#ef4444", color: "#fff", border: "1px solid transparent" },
  }[variant]
  return { ...palette, padding: "0.4rem 0.8rem", borderRadius: "0.45rem", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer" }
}
