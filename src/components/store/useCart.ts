"use client"

import { useCallback, useEffect, useState } from "react"
import { CART_EVENT, readCartLines as read, writeCartLines as write } from "@/lib/store/cartStorage"
import type { CartLine } from "@/lib/store/cartStorage"

/**
 * The cart lives in the browser only.
 *
 * It holds variant IDs and quantities — never prices. Every total the buyer is
 * shown comes back from /api/store/cart, and the order is written from a fresh
 * server-side pricing pass, so a cart edited in devtools buys nothing cheaper.
 *
 * Storage and ownership live in lib/store/cartStorage: a cart is tied to the
 * account it was filled under, and AuthContext empties it on sign-out or when a
 * different account signs in.
 *
 * Updates are immutable: each change builds a new array rather than mutating
 * the stored one, so React always sees a changed reference and re-renders.
 */

export type { CartLine }

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
