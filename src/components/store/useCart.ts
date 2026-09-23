"use client"

import { useCallback, useEffect, useState } from "react"

/**
 * The cart lives in the browser only.
 *
 * It holds variant IDs and quantities — never prices. Every total the buyer is
 * shown comes back from /api/store/cart, and the order is written from a fresh
 * server-side pricing pass, so a cart edited in devtools buys nothing cheaper.
 *
 * Updates are immutable: each change builds a new array rather than mutating
 * the stored one, so React always sees a changed reference and re-renders.
 */

const STORAGE_KEY = "grademax.cart.v1"
const CART_EVENT = "grademax:cart-changed"

export interface CartLine {
  variantId: string
  quantity: number
}

function read(): CartLine[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((l): l is CartLine =>
        typeof l === "object" && l !== null &&
        typeof (l as CartLine).variantId === "string" &&
        Number.isInteger((l as CartLine).quantity) && (l as CartLine).quantity > 0)
      .slice(0, 20)
  } catch {
    // Private browsing and blocked site data both throw here. An empty cart is
    // the right answer — it must never take the page down.
    return []
  }
}

function write(lines: CartLine[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(lines))
  } catch {
    // Storage unavailable: the cart stays in memory for this page view.
  }
  window.dispatchEvent(new CustomEvent(CART_EVENT))
}

export function useCart() {
  const [lines, setLines] = useState<CartLine[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setLines(read())
    setReady(true)
    // Keep every mounted component (the navbar badge, the cart page) in step,
    // including across tabs.
    const sync = () => setLines(read())
    window.addEventListener(CART_EVENT, sync)
    window.addEventListener("storage", sync)
    return () => {
      window.removeEventListener(CART_EVENT, sync)
      window.removeEventListener("storage", sync)
    }
  }, [])

  const add = useCallback((variantId: string, quantity = 1, replace = false) => {
    const next = read()
    const existing = next.find(l => l.variantId === variantId)
    const updated = existing
      ? next.map(l => l.variantId === variantId
          ? { ...l, quantity: replace ? quantity : Math.min(l.quantity + quantity, 50) }
          : l)
      : [...next, { variantId, quantity }]
    write(updated)
    setLines(updated)
  }, [])

  const setQuantity = useCallback((variantId: string, quantity: number) => {
    const next = quantity < 1
      ? read().filter(l => l.variantId !== variantId)
      : read().map(l => (l.variantId === variantId ? { ...l, quantity } : l))
    write(next)
    setLines(next)
  }, [])

  const remove = useCallback((variantId: string) => {
    const next = read().filter(l => l.variantId !== variantId)
    write(next)
    setLines(next)
  }, [])

  const clear = useCallback(() => {
    write([])
    setLines([])
  }, [])

  const count = lines.reduce((sum, l) => sum + l.quantity, 0)
  const has = useCallback((variantId: string) => lines.some(l => l.variantId === variantId), [lines])

  return { lines, count, ready, add, setQuantity, remove, clear, has }
}
