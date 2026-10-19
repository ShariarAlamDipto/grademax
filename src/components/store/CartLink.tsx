"use client"

import Link from "next/link"
import { useCart } from "./useCart"

/**
 * The cart entry in the navbar.
 *
 * Renders nothing until the cart has been read from storage, so the server
 * markup and the first client render agree — otherwise a stale badge count
 * flashes on every page load and React logs a hydration mismatch.
 */
export default function CartLink({ compact }: { compact?: boolean }) {
  const { count, ready } = useCart()
  if (!ready || count === 0) return null

  return (
    <Link
      href="/cart"
      aria-label={`Cart, ${count} item${count === 1 ? "" : "s"}`}
      style={{
        display: "inline-flex", alignItems: "center", gap: "0.35rem",
        padding: compact ? "0.4rem 0.7rem" : "0.45rem 0.8rem",
        borderRadius: "99px", textDecoration: "none",
        background: "var(--gm-amber-bg)", color: "var(--gm-amber)",
        border: "1px solid var(--gm-amber)",
        fontSize: "0.8rem", fontWeight: 700, whiteSpace: "nowrap",
      }}
    >
      <svg style={{ width: "0.95rem", height: "0.95rem" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
      {count}
    </Link>
  )
}
