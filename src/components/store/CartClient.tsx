"use client"

import { useCallback, useEffect, useState } from "react"
import { useCart } from "./useCart"
import { Button, Notice, PageHeader, Spinner, card } from "./StoreUI"
import { formatBdt } from "@/lib/store/format"
import type { PricedCart } from "@/lib/store/types"

/**
 * The cart page.
 *
 * Quantities live in the browser, but every figure shown here is priced by the
 * server. When the server refuses the cart — a title sold out, a product was
 * withdrawn — the message it returns is shown as-is, because it already
 * explains which item is the problem.
 */
export default function CartClient() {
  const { lines, ready, setQuantity, remove, clear } = useCart()
  const [cart, setCart] = useState<PricedCart | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const reprice = useCallback(async () => {
    if (!lines.length) { setCart(null); setLoading(false); setError(null); return }
    setLoading(true)
    try {
      const res = await fetch("/api/store/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: lines }),
      })
      const json = await res.json()
      if (!res.ok) { setError(json.error ?? "We could not price your cart."); setCart(null) }
      else { setCart(json.cart as PricedCart); setError(null) }
    } catch {
      setError("We could not reach the server. Check your connection and try again.")
    } finally {
      setLoading(false)
    }
  }, [lines])

  useEffect(() => { if (ready) void reprice() }, [ready, reprice])

  if (!ready || loading) {
    return <Shell><PageHeader title="Your cart" /><Spinner label="Pricing your cart" /></Shell>
  }

  if (!lines.length) {
    return (
      <Shell>
        <PageHeader title="Your cart" />
        <div style={card}>
          <p style={{ fontSize: "0.9rem", color: "var(--gm-text-2)", marginBottom: "1rem" }}>
            Your cart is empty.
          </p>
          <Button href="/store">Browse the books</Button>
        </div>
      </Shell>
    )
  }

  return (
    <Shell>
      <PageHeader
        title="Your cart"
        action={<Button variant="ghost" small onClick={clear}>Empty cart</Button>}
      />

      {error ? <Notice tone="red">{error}</Notice> : null}

      <div style={{ display: "grid", gap: "1.5rem", alignItems: "start" }}
           className="gm-store-product-grid">
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {(cart?.lines ?? []).map(line => (
            <div key={line.variantId} style={{ ...card, display: "flex", gap: "1rem", alignItems: "flex-start", flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 14rem", minWidth: 0 }}>
                <strong style={{ fontSize: "0.92rem", fontWeight: 700, display: "block", lineHeight: 1.4 }}>
                  {line.productTitle}
                </strong>
                <span style={{ fontSize: "0.78rem", color: "var(--gm-text-3)", display: "block", marginTop: "0.2rem" }}>
                  {line.variantLabel}
                </span>
                <span style={{ fontSize: "0.78rem", color: "var(--gm-text-2)", display: "block", marginTop: "0.4rem" }}>
                  {formatBdt(line.unitPriceBdt)} each
                </span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                {line.kind === "print" ? (
                  <div style={{ display: "flex", alignItems: "center", border: "1px solid var(--gm-border-2)", borderRadius: "0.5rem", overflow: "hidden" }}>
                    <Stepper label="−" onClick={() => setQuantity(line.variantId, line.quantity - 1)} />
                    <span style={{ padding: "0 0.75rem", fontSize: "0.85rem", fontWeight: 700, minWidth: "2rem", textAlign: "center" }}>
                      {line.quantity}
                    </span>
                    <Stepper label="+" onClick={() => setQuantity(line.variantId, line.quantity + 1)} />
                  </div>
                ) : (
                  <span style={{ fontSize: "0.78rem", color: "var(--gm-text-3)" }}>One copy</span>
                )}

                <strong style={{ fontSize: "0.95rem", minWidth: "5rem", textAlign: "right" }}>
                  {formatBdt(line.lineTotalBdt)}
                </strong>
              </div>

              <button
                onClick={() => remove(line.variantId)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--gm-text-3)", fontSize: "0.75rem", textDecoration: "underline", padding: 0 }}
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <aside style={{ ...card, position: "sticky", top: "5.5rem" }}>
          <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.9rem" }}>Summary</h2>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.4rem" }}>
            <span style={{ color: "var(--gm-text-2)" }}>Subtotal</span>
            <strong>{formatBdt(cart?.subtotalBdt ?? 0)}</strong>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.9rem" }}>
            <span style={{ color: "var(--gm-text-2)" }}>Delivery</span>
            <span style={{ color: "var(--gm-text-3)", fontSize: "0.8rem" }}>
              {cart?.hasPrint ? "At checkout" : "Free"}
            </span>
          </div>
          <Button full href="/checkout" variant="primary">Checkout</Button>
          <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.8rem", lineHeight: 1.6 }}>
            {cart?.hasDigital && cart?.hasPrint
              ? "Your cart mixes a printed book with a PDF, so payment must be by bKash or Nagad."
              : cart?.hasDigital
                ? "Digital orders have no delivery charge."
                : "Delivery is calculated once you choose your district."}
          </p>
        </aside>
      </div>
    </Shell>
  )
}

function Stepper({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      background: "var(--gm-surface-2)", border: "none", cursor: "pointer",
      color: "var(--gm-text)", padding: "0.4rem 0.7rem", fontSize: "0.95rem", lineHeight: 1,
    }}>
      {label}
    </button>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main style={{ maxWidth: "62rem", margin: "0 auto", padding: "2.5rem 1.25rem 4rem" }}>
      {children}
    </main>
  )
}
