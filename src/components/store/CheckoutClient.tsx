"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useCart } from "./useCart"
import { Button, Field, Notice, PageHeader, Spinner, card } from "./StoreUI"
import PaymentClaimForm from "./PaymentClaimForm"
import { formatBdt } from "@/lib/store/format"
import type { District, PaymentMethod, PricedCart } from "@/lib/store/types"
import type { PrefillDetails } from "@/app/checkout/page"

/**
 * Checkout is two steps on one page.
 *
 *   1. Details and payment method -> creates the order.
 *   2. The buyer sends money and reports the Transaction ID.
 *
 * Step 2 exists because bKash and Nagad are being collected by hand: the order
 * has to be created first so there is something to attach the payment to, and
 * so the buyer has an order number to quote if anything goes wrong. Nothing is
 * shipped or unlocked until an admin verifies the payment.
 */

interface Props {
  districts: District[]
  storeEnabled: boolean
  wallets: { bkash: string; nagad: string }
  instructions: string
  slaHours: number
  prefill: PrefillDetails
}

interface PlacedOrder {
  orderNumber: string
  totalBdt: number
  hasDigital: boolean
  hasPrint: boolean
  paymentMethod: PaymentMethod
  payTo: string | null
}

export default function CheckoutClient({ districts, storeEnabled, wallets, instructions, slaHours, prefill }: Props) {
  const { lines, ready, clear } = useCart()

  const [cart, setCart] = useState<PricedCart | null>(null)
  const [pricingError, setPricingError] = useState<string | null>(null)
  const [pricing, setPricing] = useState(true)

  const [name, setName] = useState(prefill.name)
  const [phone, setPhone] = useState(prefill.phone)
  const [altPhone, setAltPhone] = useState("")
  const [email, setEmail] = useState(prefill.email)
  const [districtId, setDistrictId] = useState<number | "">(prefill.districtId)
  const [city, setCity] = useState(prefill.city)
  const [area, setArea] = useState(prefill.area)
  const [houseNo, setHouseNo] = useState(prefill.houseNo)
  const [roadNo, setRoadNo] = useState(prefill.roadNo)
  const [landmark, setLandmark] = useState(prefill.landmark)
  const [postcode, setPostcode] = useState(prefill.postcode)
  const [address, setAddress] = useState("")
  const [notes, setNotes] = useState("")
  const [method, setMethod] = useState<PaymentMethod>("bkash")
  const [honeypot, setHoneypot] = useState("")

  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [placed, setPlaced] = useState<PlacedOrder | null>(null)

  const needsAddress = cart?.hasPrint ?? false

  /** Re-price whenever the cart or the chosen district changes. */
  const reprice = useCallback(async () => {
    if (!lines.length) { setCart(null); setPricing(false); return }
    setPricing(true)
    try {
      const res = await fetch("/api/store/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: lines, districtId: districtId || undefined }),
      })
      const json = await res.json()
      if (!res.ok) { setPricingError(json.error ?? "We could not price your cart."); setCart(null) }
      else { setCart(json.cart as PricedCart); setPricingError(null) }
    } catch {
      setPricingError("We could not reach the server. Check your connection and try again.")
    } finally {
      setPricing(false)
    }
  }, [lines, districtId])

  useEffect(() => { if (ready) void reprice() }, [ready, reprice])

  // Keep the selected method legal: adding a PDF to the cart removes cash on
  // delivery, and the buyer must not be left on a method the server will refuse.
  useEffect(() => {
    if (cart && !cart.allowedPaymentMethods.includes(method)) {
      setMethod(cart.allowedPaymentMethods[0] ?? "bkash")
    }
  }, [cart, method])

  const selectedDistrict = useMemo(
    () => districts.find(d => d.id === districtId),
    [districts, districtId]
  )

  async function placeOrder() {
    if (!cart) return
    setFormError(null)
    setSubmitting(true)
    try {
      const res = await fetch("/api/store/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: lines,
          customer: { name, phone, email, altPhone: altPhone || undefined },
          delivery: needsAddress
            ? {
                districtId: Number(districtId),
                city,
                area,
                houseNo,
                roadNo: roadNo || undefined,
                landmark: landmark || undefined,
                postcode: postcode || undefined,
                addressLine: address || undefined,
              }
            : undefined,
          paymentMethod: method,
          notes: notes || undefined,
          website: honeypot,
          source: {
            path: typeof window !== "undefined" ? window.location.pathname : undefined,
            referrer: typeof document !== "undefined" ? document.referrer.slice(0, 300) : undefined,
          },
        }),
      })
      const json = await res.json()
      if (res.status === 401 || json?.requiresAccount) {
        // The session expired between loading the page and submitting it.
        window.location.href = `/login?next=${encodeURIComponent("/checkout")}`
        return
      }
      if (!res.ok) { setFormError(json.error ?? "We could not place your order."); return }

      setPlaced({
        orderNumber: json.orderNumber,
        totalBdt: json.totalBdt,
        hasDigital: json.hasDigital,
        hasPrint: json.hasPrint,
        paymentMethod: json.paymentMethod,
        payTo: json.payTo,
      })
      clear()
    } catch {
      setFormError("We could not reach the server. Your card has not been charged — nothing was taken.")
    } finally {
      setSubmitting(false)
    }
  }

  if (!storeEnabled) {
    return (
      <Shell>
        <PageHeader title="Checkout" />
        <Notice tone="amber">The shop is not open yet. Please check back shortly.</Notice>
      </Shell>
    )
  }

  if (placed) {
    return (
      <Shell>
        <PaymentStep order={placed} wallets={wallets} instructions={instructions} slaHours={slaHours} />
      </Shell>
    )
  }

  if (!ready || pricing) return <Shell><Spinner label="Checking your cart" /></Shell>

  if (!lines.length || !cart) {
    return (
      <Shell>
        <PageHeader title="Checkout" />
        <div style={card}>
          <p style={{ fontSize: "0.9rem", color: "var(--gm-text-2)", marginBottom: "1rem" }}>
            {pricingError ?? "Your cart is empty."}
          </p>
          <Button href="/store">Browse the books</Button>
        </div>
      </Shell>
    )
  }

  const canSubmit =
    name.trim().length >= 2 &&
    phone.trim().length >= 6 &&
    email.trim().includes("@") &&
    (!needsAddress || (
      districtId !== "" &&
      city.trim().length >= 2 &&
      area.trim().length >= 2 &&
      houseNo.trim().length >= 1
    )) &&
    !submitting

  return (
    <Shell>
      <PageHeader title="Checkout" lead="Your order is confirmed by hand, so nothing is charged automatically." />

      {formError ? <Notice tone="red">{formError}</Notice> : null}

      <div style={{ display: "grid", gap: "1.5rem", alignItems: "start" }}
           className="gm-store-product-grid">
        <div style={card}>
          <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "1rem" }}>Your details</h2>

          <Field label="Full name" required>
            <input className="gm-input" value={name} onChange={e => setName(e.target.value)}
                   autoComplete="name" placeholder="e.g. Rafid Hasan" />
          </Field>

          <Field label="Mobile number" required hint="We confirm your order on this number, so use the one you pay from if you can.">
            <input className="gm-input" value={phone} onChange={e => setPhone(e.target.value)}
                   autoComplete="tel" inputMode="tel" placeholder="01712345678" />
          </Field>

          <Field label="Email" required hint="Your receipt and any delivery updates go here.">
            <input className="gm-input" value={email} onChange={e => setEmail(e.target.value)}
                   autoComplete="email" inputMode="email" type="email" placeholder="you@example.com" />
          </Field>

          <Field label="Another number" hint="Optional. Used only if we cannot reach you on the first one.">
            <input className="gm-input" value={altPhone} onChange={e => setAltPhone(e.target.value)}
                   autoComplete="tel" inputMode="tel" placeholder="01812345678" />
          </Field>

          {needsAddress ? (
            <>
              <h2 style={{ fontSize: "0.95rem", fontWeight: 700, margin: "1.5rem 0 0.35rem" }}>
                Delivery address
              </h2>
              <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "1rem", lineHeight: 1.6 }}>
                We deliver anywhere in Bangladesh. The more precise this is, the
                better the chance the courier finds you first time.
              </p>

              <Field label="District" required>
                <select className="gm-select" value={districtId}
                        onChange={e => setDistrictId(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Choose your district…</option>
                  {districts.map(d => (
                    <option key={d.id} value={d.id}>{d.name}{d.is_metro ? " (city)" : ""}</option>
                  ))}
                </select>
              </Field>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <Field label="City / upazila / thana" required>
                  <input className="gm-input" value={city} onChange={e => setCity(e.target.value)}
                         autoComplete="address-level2" placeholder="e.g. Dhaka" />
                </Field>
                <Field label="Area" required>
                  <input className="gm-input" value={area} onChange={e => setArea(e.target.value)}
                         autoComplete="address-level3" placeholder="e.g. Dhanmondi" />
                </Field>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <Field label="House / flat number" required>
                  <input className="gm-input" value={houseNo} onChange={e => setHouseNo(e.target.value)}
                         placeholder="e.g. 12/A, Flat 4B" />
                </Field>
                <Field label="Road / street number">
                  <input className="gm-input" value={roadNo} onChange={e => setRoadNo(e.target.value)}
                         placeholder="e.g. Road 5" />
                </Field>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <Field label="Nearest landmark" hint="Couriers find addresses by landmark here.">
                  <input className="gm-input" value={landmark} onChange={e => setLandmark(e.target.value)}
                         placeholder="e.g. beside Rapa Plaza" />
                </Field>
                <Field label="Postcode">
                  <input className="gm-input" value={postcode} onChange={e => setPostcode(e.target.value)}
                         autoComplete="postal-code" inputMode="numeric" placeholder="e.g. 1209" />
                </Field>
              </div>

              <Field label="Anything else about the address">
                <textarea className="gm-input" rows={2} value={address}
                          onChange={e => setAddress(e.target.value)} style={{ resize: "vertical" }}
                          placeholder="Building name, floor, or directions" />
              </Field>
            </>
          ) : (
            <Notice tone="blue">
              This order is digital only, so there is nothing to deliver and no delivery charge.
            </Notice>
          )}

          <h2 style={{ fontSize: "0.95rem", fontWeight: 700, margin: "1.5rem 0 1rem" }}>Payment</h2>

          {cart.hasDigital && cart.hasPrint ? (
            <Notice tone="amber">
              Your cart has both a printed book and a PDF, so cash on delivery is not available —
              we cannot hand over a download before payment. Pay with bKash or Nagad and both are released together.
            </Notice>
          ) : null}

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem" }}>
            {cart.allowedPaymentMethods.map(m => (
              <PaymentOption key={m} method={m} selected={method === m} onSelect={() => setMethod(m)}
                             wallets={wallets} />
            ))}
          </div>

          <Field label="Order notes">
            <textarea className="gm-input" rows={2} value={notes}
                      onChange={e => setNotes(e.target.value)} style={{ resize: "vertical" }}
                      placeholder="Anything we should know" />
          </Field>

          {/* Honeypot — hidden from people, filled in by naive bots. */}
          <input
            type="text" value={honeypot} onChange={e => setHoneypot(e.target.value)}
            tabIndex={-1} autoComplete="off" aria-hidden="true"
            style={{ position: "absolute", left: "-9999px", width: "1px", height: "1px", opacity: 0 }}
          />

          <Button full onClick={placeOrder} disabled={!canSubmit}>
            {submitting ? "Placing your order…" : `Place order · ${formatBdt(cart.totalBdt)}`}
          </Button>
        </div>

        <OrderSummary cart={cart} districtKnown={Boolean(selectedDistrict)} needsAddress={needsAddress} />
      </div>
    </Shell>
  )
}

function PaymentOption({
  method, selected, onSelect, wallets,
}: {
  method: PaymentMethod
  selected: boolean
  onSelect: () => void
  wallets: { bkash: string; nagad: string }
}) {
  const copy: Record<PaymentMethod, { title: string; body: string }> = {
    bkash: { title: "bKash", body: wallets.bkash ? `Send money to ${wallets.bkash}, then enter the Transaction ID.` : "Send money, then enter the Transaction ID." },
    nagad: { title: "Nagad", body: wallets.nagad ? `Send money to ${wallets.nagad}, then enter the Transaction ID.` : "Send money, then enter the Transaction ID." },
    cod:   { title: "Cash on delivery", body: "Pay the courier when your book arrives." },
  }
  return (
    <button type="button" onClick={onSelect} style={{
      display: "block", width: "100%", textAlign: "left", cursor: "pointer",
      padding: "0.7rem 0.8rem", borderRadius: "0.6rem",
      border: `1px solid ${selected ? "var(--gm-amber)" : "var(--gm-border-2)"}`,
      background: selected ? "var(--gm-amber-bg)" : "var(--gm-surface-2)",
      color: "var(--gm-text)",
    }}>
      <strong style={{ fontSize: "0.85rem", fontWeight: 700 }}>{copy[method].title}</strong>
      <span style={{ display: "block", fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.15rem" }}>
        {copy[method].body}
      </span>
    </button>
  )
}

function OrderSummary({ cart, districtKnown, needsAddress }: { cart: PricedCart; districtKnown: boolean; needsAddress: boolean }) {
  return (
    <aside style={{ ...card, position: "sticky", top: "5.5rem" }}>
      <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.9rem" }}>Your order</h2>

      {cart.lines.map(line => (
        <div key={line.variantId} style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", marginBottom: "0.7rem" }}>
          <span style={{ minWidth: 0 }}>
            <span style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, lineHeight: 1.35 }}>
              {line.productTitle}
            </span>
            <span style={{ display: "block", fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.1rem" }}>
              {line.kind === "print" ? "Printed" : "PDF"} × {line.quantity}
            </span>
          </span>
          <strong style={{ fontSize: "0.82rem", whiteSpace: "nowrap" }}>{formatBdt(line.lineTotalBdt)}</strong>
        </div>
      ))}

      <div style={{ borderTop: "1px solid var(--gm-border)", marginTop: "0.9rem", paddingTop: "0.9rem", fontSize: "0.82rem" }}>
        <Row label="Subtotal" value={formatBdt(cart.subtotalBdt)} />
        <Row
          label="Delivery"
          value={!needsAddress ? "Free" : districtKnown ? formatBdt(cart.deliveryBdt) : "Choose a district"}
          muted={needsAddress && !districtKnown}
        />
        <div style={{ borderTop: "1px solid var(--gm-border)", marginTop: "0.6rem", paddingTop: "0.6rem" }}>
          <Row label="Total" value={formatBdt(cart.totalBdt)} strong />
        </div>
      </div>

      <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.9rem", lineHeight: 1.6 }}>
        <Link href="/cart" className="gm-link">Edit your cart</Link>
      </p>
    </aside>
  )
}

function Row({ label, value, strong, muted }: { label: string; value: string; strong?: boolean; muted?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.35rem" }}>
      <span style={{ color: muted ? "var(--gm-text-3)" : "var(--gm-text-2)", fontWeight: strong ? 700 : 400 }}>{label}</span>
      <span style={{ fontWeight: strong ? 800 : 600, fontSize: strong ? "1rem" : undefined }}>{value}</span>
    </div>
  )
}

/** Step 2 — the buyer has an order and now reports their payment. */
function PaymentStep({
  order, wallets, instructions, slaHours,
}: {
  order: PlacedOrder
  wallets: { bkash: string; nagad: string }
  instructions: string
  slaHours: number
}) {
  const [paid, setPaid] = useState(false)
  const isCod = order.paymentMethod === "cod"
  const wallet = order.payTo
    || (order.paymentMethod === "bkash" ? wallets.bkash : order.paymentMethod === "nagad" ? wallets.nagad : null)

  return (
    <>
      <PageHeader
        title="Order placed"
        lead={`Your order number is ${order.orderNumber}. Keep it — you will need it to track your order.`}
      />

      <Notice tone="green">
        <strong>{order.orderNumber}</strong> · {formatBdt(order.totalBdt)}
      </Notice>

      <div style={card}>
        {isCod ? (
          <>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.6rem" }}>What happens next</h2>
            <p style={{ fontSize: "0.88rem", color: "var(--gm-text-2)", lineHeight: 1.7 }}>
              We will call you on the number you gave to confirm the order, then send it out.
              Pay the courier {formatBdt(order.totalBdt)} when your book arrives.
            </p>
          </>
        ) : paid ? (
          <>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.6rem" }}>Payment recorded</h2>
            <p style={{ fontSize: "0.88rem", color: "var(--gm-text-2)", lineHeight: 1.7 }}>
              We are checking your payment now — this is done by hand, usually within {slaHours} hours.
              {order.hasDigital ? " Your download unlocks as soon as it is confirmed." : ""}
              {order.hasPrint ? " We will call you to arrange delivery." : ""}
            </p>
            <p style={{ fontSize: "0.82rem", color: "var(--gm-text-3)", marginTop: "0.8rem", lineHeight: 1.6 }}>
              You do not need to pay again. Track the status any time with your order number
              and phone number.
            </p>
          </>
        ) : (
          <>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.75rem" }}>
              Send {formatBdt(order.totalBdt)} with {order.paymentMethod === "bkash" ? "bKash" : "Nagad"}
            </h2>
            <PaymentClaimForm
              orderNumber={order.orderNumber}
              totalBdt={order.totalBdt}
              method={order.paymentMethod as "bkash" | "nagad"}
              payTo={wallet}
              instructions={instructions}
              onSubmitted={() => setPaid(true)}
            />
            <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.9rem", lineHeight: 1.6 }}>
              Not ready to pay? Your order is saved. Come back to{" "}
              <Link href={`/store/orders?order=${encodeURIComponent(order.orderNumber)}`} className="gm-link">
                {order.orderNumber}
              </Link>{" "}
              and enter the Transaction ID any time in the next 48 hours.
            </p>
          </>
        )}

        {(isCod || paid) ? (
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <Button href={`/store/orders?order=${encodeURIComponent(order.orderNumber)}`}>Track this order</Button>
            <Button href="/store" variant="secondary">Keep browsing</Button>
          </div>
        ) : null}
      </div>
    </>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main style={{ maxWidth: "62rem", margin: "0 auto", padding: "2.5rem 1.25rem 4rem" }}>
      {children}
    </main>
  )
}
