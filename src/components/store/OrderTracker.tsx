"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Badge, Button, Field, Notice, PageHeader, card } from "./StoreUI"
import PaymentClaimForm from "./PaymentClaimForm"
import { formatBdt, formatDhakaDate } from "@/lib/store/format"
import {
  ORDER_STATUS_FLOW, ORDER_STATUS_LABEL, PAYMENT_STATUS_LABEL,
  type OrderStatus, type PaymentStatus,
} from "@/lib/store/types"

/**
 * Guest order tracking, and the buyer's route back to a payment they never
 * finished. It is also where digital downloads are collected: proving the order
 * is yours mints fresh, short-lived download links.
 */

interface MyOrder {
  orderNumber: string
  placedAt: string
  totalBdt: number
  paymentStatus: PaymentStatus
  orderStatus: OrderStatus
  titles: string[]
}

interface TrackedOrder {
  orderNumber: string
  placedAt: string
  customerName: string
  phone: string
  district: string | null
  subtotalBdt: number
  deliveryBdt: number
  totalBdt: number
  paymentMethod: "bkash" | "nagad" | "cod"
  paymentStatus: PaymentStatus
  orderStatus: OrderStatus
  courierName: string | null
  trackingCode: string | null
  hasPrint: boolean
  hasDigital: boolean
  items: { title: string; variant: string; kind: string; quantity: number; lineTotalBdt: number }[]
  downloads: { productTitle: string; url: string; remaining: number }[]
}

export default function OrderTracker() {
  const params = useSearchParams()
  const [orderNumber, setOrderNumber] = useState(params.get("order") ?? "")
  const [phone, setPhone] = useState("")
  const [order, setOrder] = useState<TrackedOrder | null>(null)
  const [payTo, setPayTo] = useState<string | null>(null)
  const [slaHours, setSlaHours] = useState(12)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [mine, setMine] = useState<MyOrder[] | null>(null)

  useEffect(() => {
    const fromUrl = params.get("order")
    if (fromUrl) setOrderNumber(fromUrl)
  }, [params])

  // Ordering requires an account, so a signed-in buyer should never have to
  // remember an order number. A 401 here simply means they are signed out.
  useEffect(() => {
    let cancelled = false
    fetch("/api/store/orders/mine")
      .then(r => (r.ok ? r.json() : { orders: [] }))
      .then(d => { if (!cancelled) setMine(d.orders ?? []) })
      .catch(() => { if (!cancelled) setMine([]) })
    return () => { cancelled = true }
  }, [])

  async function lookup() {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch("/api/store/orders/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ orderNumber: orderNumber.trim(), phone: phone.trim() }),
      })
      const json = await res.json()
      if (!res.ok) { setError(json.error ?? "We could not find that order."); setOrder(null); return }
      setOrder(json.order as TrackedOrder)
      setPayTo(json.payTo ?? null)
      setSlaHours(json.slaHours ?? 12)
    } catch {
      setError("We could not reach the server. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: "48rem", margin: "0 auto", padding: "2.5rem 1.25rem 4rem" }}>
      <PageHeader
        title="Track your order"
        lead="Enter your order number and the phone number you ordered with."
      />

      {mine && mine.length > 0 ? (
        <section style={{ ...card, marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.75rem" }}>Your orders</h2>
          {mine.map(o => (
            <button
              key={o.orderNumber}
              onClick={() => { setOrderNumber(o.orderNumber); setError(null) }}
              style={{
                display: "flex", width: "100%", textAlign: "left", cursor: "pointer",
                justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap",
                background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)",
                borderRadius: "0.5rem", padding: "0.6rem 0.75rem", marginBottom: "0.5rem",
                color: "var(--gm-text)",
              }}
            >
              <span style={{ minWidth: 0 }}>
                <strong style={{ fontSize: "0.82rem", display: "block" }}>{o.orderNumber}</strong>
                <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)" }}>
                  {o.titles.join(", ") || "—"}
                </span>
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
                <Badge tone={o.paymentStatus === "verified" || o.paymentStatus === "paid_on_delivery" ? "green"
                           : o.paymentStatus === "submitted" ? "amber" : "neutral"}>
                  {PAYMENT_STATUS_LABEL[o.paymentStatus]}
                </Badge>
                <strong style={{ fontSize: "0.82rem" }}>{formatBdt(o.totalBdt)}</strong>
              </span>
            </button>
          ))}
          <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.5rem" }}>
            Pick an order, then enter the phone number you ordered with to see it in full.
          </p>
        </section>
      ) : null}

      <div style={{ ...card, marginBottom: "1.5rem" }}>
        <Field label="Order number" required>
          <input className="gm-input" value={orderNumber}
                 onChange={e => setOrderNumber(e.target.value.toUpperCase())}
                 placeholder="GM-1042-K7QX" style={{ letterSpacing: "0.04em" }} />
        </Field>
        <Field label="Mobile number" required>
          <input className="gm-input" value={phone} onChange={e => setPhone(e.target.value)}
                 inputMode="tel" placeholder="01712345678" />
        </Field>
        {error ? <Notice tone="red">{error}</Notice> : null}
        <Button full onClick={lookup} disabled={loading || orderNumber.trim().length < 4 || phone.trim().length < 6}>
          {loading ? "Looking…" : "Find my order"}
        </Button>
      </div>

      {order ? <OrderDetail order={order} payTo={payTo} slaHours={slaHours} onPaid={lookup} /> : null}
    </main>
  )
}

function OrderDetail({
  order, payTo, slaHours, onPaid,
}: {
  order: TrackedOrder
  payTo: string | null
  slaHours: number
  onPaid: () => void
}) {
  const paymentTone =
    order.paymentStatus === "verified" || order.paymentStatus === "paid_on_delivery" ? "green"
    : order.paymentStatus === "rejected" ? "red"
    : order.paymentStatus === "submitted" ? "amber"
    : "neutral"

  const needsPayment = order.paymentStatus === "awaiting_payment" && order.paymentMethod !== "cod"

  return (
    <>
      <section style={{ ...card, marginBottom: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          <div>
            <strong style={{ fontSize: "1.1rem", fontWeight: 800, letterSpacing: "0.02em" }}>{order.orderNumber}</strong>
            <span style={{ display: "block", fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>
              Placed {formatDhakaDate(order.placedAt)}
            </span>
          </div>
          <Badge tone={paymentTone}>{PAYMENT_STATUS_LABEL[order.paymentStatus]}</Badge>
        </div>

        {order.hasPrint && order.orderStatus !== "cancelled" ? (
          <ProgressTrail current={order.orderStatus} />
        ) : null}

        {order.orderStatus === "cancelled" ? (
          <Notice tone="red">This order was cancelled. If that is unexpected, contact us with your order number.</Notice>
        ) : null}

        {order.courierName || order.trackingCode ? (
          <Notice tone="blue">
            Sent with {order.courierName ?? "our courier"}
            {order.trackingCode ? <> · tracking <strong>{order.trackingCode}</strong></> : null}
          </Notice>
        ) : null}

        <div style={{ borderTop: "1px solid var(--gm-border)", paddingTop: "0.9rem", marginTop: "0.9rem" }}>
          {order.items.map((item, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: "1rem", marginBottom: "0.5rem", fontSize: "0.85rem" }}>
              <span>
                {item.title}
                <span style={{ color: "var(--gm-text-3)" }}> · {item.kind === "print" ? "Printed" : "PDF"} × {item.quantity}</span>
              </span>
              <strong style={{ whiteSpace: "nowrap" }}>{formatBdt(item.lineTotalBdt)}</strong>
            </div>
          ))}
          <div style={{ borderTop: "1px solid var(--gm-border)", marginTop: "0.7rem", paddingTop: "0.7rem", display: "flex", justifyContent: "space-between", fontSize: "0.95rem" }}>
            <strong>Total</strong>
            <strong style={{ fontWeight: 800 }}>{formatBdt(order.totalBdt)}</strong>
          </div>
        </div>
      </section>

      {order.downloads.length > 0 ? (
        <section style={{ ...card, marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.3rem" }}>Your downloads</h2>
          <p style={{ fontSize: "0.78rem", color: "var(--gm-text-3)", marginBottom: "0.9rem", lineHeight: 1.6 }}>
            Links are valid for a few minutes. Come back to this page any time for fresh ones.
          </p>
          {order.downloads.map((d, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap", marginBottom: "0.6rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{d.productTitle}</span>
              <span style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>{d.remaining} left</span>
                <a href={d.url} style={{
                  background: "var(--gm-amber)", color: "#1a1206", padding: "0.4rem 0.8rem",
                  borderRadius: "0.5rem", fontSize: "0.8rem", fontWeight: 600, textDecoration: "none",
                }}>
                  Download
                </a>
              </span>
            </div>
          ))}
        </section>
      ) : null}

      {order.hasDigital && order.paymentStatus === "submitted" ? (
        <Notice tone="amber">
          We are checking your payment — usually within {slaHours} hours. Your download appears here
          as soon as it is confirmed. You do not need to pay again.
        </Notice>
      ) : null}

      {needsPayment ? (
        <PayNow order={order} payTo={payTo} onPaid={onPaid} />
      ) : null}
    </>
  )
}

function ProgressTrail({ current }: { current: OrderStatus }) {
  const index = ORDER_STATUS_FLOW.indexOf(current)
  return (
    <div style={{ display: "flex", gap: "0.3rem", marginBottom: "1rem" }}>
      {ORDER_STATUS_FLOW.map((status, i) => (
        <div key={status} style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            height: "3px", borderRadius: "2px", marginBottom: "0.35rem",
            background: i <= index ? "var(--gm-amber)" : "var(--gm-border-2)",
          }} />
          <span style={{
            fontSize: "0.65rem",
            color: i <= index ? "var(--gm-text-2)" : "var(--gm-text-3)",
            fontWeight: i === index ? 700 : 400,
          }}>
            {ORDER_STATUS_LABEL[status]}
          </span>
        </div>
      ))}
    </div>
  )
}

function PayNow({ order, payTo, onPaid }: { order: TrackedOrder; payTo: string | null; onPaid: () => void }) {
  if (order.paymentMethod === "cod") return null
  return (
    <section style={card}>
      <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.75rem" }}>
        Complete your payment
      </h2>
      <PaymentClaimForm
        orderNumber={order.orderNumber}
        totalBdt={order.totalBdt}
        method={order.paymentMethod}
        payTo={payTo}
        onSubmitted={onPaid}
      />
    </section>
  )
}
