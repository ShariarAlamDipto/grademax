"use client"

import Link from "next/link"
import type { CSSProperties, ReactNode } from "react"
import { formatBdt } from "@/lib/store/format"

/**
 * Shared presentational pieces for the store.
 *
 * Kept in one place so the catalogue, the product page, the cart and the order
 * tracker cannot drift apart visually. Styling follows the rest of the site:
 * inline styles over the --gm-* custom properties, so light and dark themes
 * both work without a second stylesheet.
 */

export const card: CSSProperties = {
  background: "var(--gm-card-bg)",
  border: "1px solid var(--gm-border)",
  borderRadius: "0.85rem",
  padding: "1.25rem",
}

export function Price({ amount, compareAt }: { amount: number; compareAt?: number | null }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "baseline", gap: "0.5rem" }}>
      <strong style={{ fontSize: "1.35rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
        {formatBdt(amount)}
      </strong>
      {compareAt && compareAt > amount ? (
        <span style={{ fontSize: "0.9rem", color: "var(--gm-text-3)", textDecoration: "line-through" }}>
          {formatBdt(compareAt)}
        </span>
      ) : null}
    </span>
  )
}

const TONES = {
  neutral: { bg: "var(--gm-surface-2)", fg: "var(--gm-text-2)" },
  amber:   { bg: "var(--gm-amber-bg)",  fg: "var(--gm-amber)" },
  blue:    { bg: "var(--gm-blue-bg)",   fg: "var(--gm-blue)" },
  green:   { bg: "var(--gm-green-bg)",  fg: "var(--gm-green)" },
  red:     { bg: "#ef444422",           fg: "#ef4444" },
} as const

export type Tone = keyof typeof TONES

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  const t = TONES[tone]
  return (
    <span style={{
      background: t.bg, color: t.fg,
      borderRadius: "0.35rem", padding: "0.15rem 0.5rem",
      fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.02em",
      whiteSpace: "nowrap",
    }}>
      {children}
    </span>
  )
}

export function Button({
  children, onClick, href, variant = "primary", disabled, type = "button", full, small,
}: {
  children: ReactNode
  onClick?: () => void
  href?: string
  variant?: "primary" | "secondary" | "ghost" | "danger"
  disabled?: boolean
  type?: "button" | "submit"
  full?: boolean
  small?: boolean
}) {
  const palette: Record<string, CSSProperties> = {
    primary:   { background: "var(--gm-amber)", color: "#1a1206", border: "1px solid transparent" },
    secondary: { background: "var(--gm-surface-2)", color: "var(--gm-text)", border: "1px solid var(--gm-border-2)" },
    ghost:     { background: "transparent", color: "var(--gm-text-2)", border: "1px solid var(--gm-border)" },
    danger:    { background: "#ef4444", color: "#fff", border: "1px solid transparent" },
  }
  const style: CSSProperties = {
    ...palette[variant],
    padding: small ? "0.4rem 0.7rem" : "0.6rem 1.1rem",
    borderRadius: "0.55rem",
    fontSize: small ? "0.8rem" : "0.875rem",
    fontWeight: 600,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.55 : 1,
    width: full ? "100%" : undefined,
    textAlign: "center",
    textDecoration: "none",
    display: "inline-block",
    transition: "filter 0.15s ease",
  }

  if (href && !disabled) {
    return <Link href={href} style={style}>{children}</Link>
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} style={style}>
      {children}
    </button>
  )
}

export function Field({
  label, children, hint, error, required,
}: {
  label: string
  children: ReactNode
  hint?: string
  error?: string | null
  required?: boolean
}) {
  return (
    <label style={{ display: "block", marginBottom: "0.9rem" }}>
      <span style={{
        display: "block", fontSize: "0.78rem", fontWeight: 600,
        color: "var(--gm-text-2)", marginBottom: "0.3rem",
      }}>
        {label}
        {required ? <span style={{ color: "var(--gm-amber)" }}> *</span> : null}
      </span>
      {children}
      {hint && !error ? (
        <span style={{ display: "block", fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.25rem" }}>
          {hint}
        </span>
      ) : null}
      {error ? (
        <span style={{ display: "block", fontSize: "0.72rem", color: "#ef4444", marginTop: "0.25rem" }}>
          {error}
        </span>
      ) : null}
    </label>
  )
}

export function Notice({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  const t = TONES[tone]
  return (
    <div style={{
      background: t.bg,
      border: `1px solid ${t.fg}33`,
      color: "var(--gm-text)",
      borderRadius: "0.6rem",
      padding: "0.75rem 0.9rem",
      fontSize: "0.85rem",
      lineHeight: 1.5,
      marginBottom: "1rem",
    }}>
      {children}
    </div>
  )
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <p style={{ color: "var(--gm-text-3)", fontSize: "0.85rem", padding: "2rem 0", textAlign: "center" }}>
      {label}…
    </p>
  )
}

export function PageHeader({ title, lead, action }: { title: string; lead?: string; action?: ReactNode }) {
  return (
    <header style={{
      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
      gap: "1rem", flexWrap: "wrap", marginBottom: "1.75rem",
    }}>
      <div style={{ minWidth: 0 }}>
        <h1 style={{ fontSize: "1.9rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: lead ? "0.4rem" : 0 }}>
          {title}
        </h1>
        {lead ? (
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.95rem", maxWidth: "58ch", lineHeight: 1.55 }}>
            {lead}
          </p>
        ) : null}
      </div>
      {action}
    </header>
  )
}
