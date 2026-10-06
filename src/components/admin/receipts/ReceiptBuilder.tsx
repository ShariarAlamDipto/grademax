"use client"

import "./receipt.css"
import Link from "next/link"
import { useCallback, useEffect, useMemo, useState } from "react"
import { createPortal } from "react-dom"
import { useSearchParams } from "next/navigation"
import { Bricolage_Grotesque, DM_Mono, Hind_Siliguri } from "next/font/google"
import { DHAKA_TZ } from "@/lib/store/format"
import { blankReceipt, computeTotals, emptyItem, type ReceiptDraft } from "@/lib/receipts/receiptMath"
import { receiptFromOrder, type OrderForReceipt } from "@/lib/receipts/fromOrder"
import ReceiptForm, { btn } from "./ReceiptForm"
import ReceiptSheet from "./ReceiptSheet"

/**
 * A4 receipts for booklet printing (/admin/receipts).
 *
 * Works for walk-in print jobs typed in by hand, and for store orders: give
 * it an order number (or arrive from the order drawer's "Make receipt" link)
 * and the lines, delivery and payment are filled in from the order.
 *
 * Printing: the sheet is rendered a second time straight under <body>, and the
 * print stylesheet hides every other child of <body>. Hiding the admin chrome
 * by visibility instead would leave its height in place and spill the receipt
 * onto extra pages.
 */

const display = Bricolage_Grotesque({ subsets: ["latin"], weight: ["600", "800"], variable: "--font-gmr-display" })
const mono = DM_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-gmr-mono" })
const body = Hind_Siliguri({ subsets: ["latin", "bengali"], weight: ["400", "500", "600"], variable: "--font-gmr-body" })
const FONT_VARS = `${display.variable} ${mono.variable} ${body.variable}`

const DRAFT_KEY = "gm-admin-receipt-draft-v1"

const dhakaToday = () => new Date().toLocaleDateString("en-CA", { timeZone: DHAKA_TZ })

/** A stored draft is browser data, so rebuild it field by field rather than trust its shape. */
function readStoredDraft(): ReceiptDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== "object") return null
    const base = blankReceipt(dhakaToday())
    const stored = parsed as Record<string, unknown>
    const merged = { ...base } as Record<string, unknown>
    for (const key of Object.keys(base) as (keyof ReceiptDraft)[]) {
      if (key === "items") continue
      if (typeof stored[key] === typeof base[key]) merged[key] = stored[key]
    }
    const items = Array.isArray(stored.items)
      ? stored.items
          .filter((it): it is Record<string, unknown> => !!it && typeof it === "object")
          .map(it => ({
            name: String(it.name ?? ""),
            spec: String(it.spec ?? ""),
            qty: Number(it.qty) || 0,
            rate: Number(it.rate) || 0,
          }))
      : []
    return { ...(merged as unknown as ReceiptDraft), items: items.length ? items : [emptyItem()] }
  } catch {
    return null
  }
}

export default function ReceiptBuilder() {
  const searchParams = useSearchParams()
  const [draft, setDraft] = useState<ReceiptDraft>(() => blankReceipt(dhakaToday()))
  const [mounted, setMounted] = useState(false)
  const [orderQuery, setOrderQuery] = useState("")
  const [lookup, setLookup] = useState<{ busy: boolean; message: string | null; isError: boolean }>(
    { busy: false, message: null, isError: false },
  )

  const totals = useMemo(() => computeTotals(draft), [draft])

  const loadOrder = useCallback(async (orderNumber: string) => {
    const q = orderNumber.trim()
    if (!q) return
    setLookup({ busy: true, message: null, isError: false })
    try {
      const res = await fetch(`/api/admin/store/orders?${new URLSearchParams({ q, limit: "10" })}`)
      const json = await res.json()
      if (!res.ok) {
        setLookup({ busy: false, message: json.error ?? "Could not look up that order.", isError: true })
        return
      }
      const orders: OrderForReceipt[] = json.orders ?? []
      const match = orders.find(o => o.order_number.toLowerCase() === q.toLowerCase()) ?? (orders.length === 1 ? orders[0] : null)
      if (!match) {
        setLookup({
          busy: false,
          message: orders.length ? `${orders.length} orders match "${q}". Type the full order number.` : `No order matches "${q}".`,
          isError: true,
        })
        return
      }
      setDraft(prev => receiptFromOrder(match, { ...blankReceipt(dhakaToday()), shop: prev.shop, shopSub: prev.shopSub, note: prev.note }))
      setOrderQuery(match.order_number)
      setLookup({ busy: false, message: `Filled in from order ${match.order_number}. Check it, then print.`, isError: false })
    } catch (err) {
      console.error("[admin/receipts] order lookup failed:", err)
      setLookup({ busy: false, message: "Could not reach the server. Check your connection and try again.", isError: true })
    }
  }, [])

  // On first load: an order from the link wins, otherwise restore the saved draft.
  useEffect(() => {
    setMounted(true)
    const fromLink = searchParams.get("order")
    if (fromLink) {
      setOrderQuery(fromLink)
      void loadOrder(fromLink)
      return
    }
    const stored = readStoredDraft()
    if (stored) setDraft(stored)
    // Run once on mount; later changes to the query string are not expected here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!mounted) return
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
    } catch {
      // Storage blocked (private window): the draft just isn't kept between visits.
    }
  }, [draft, mounted])

  const startNew = () => {
    setDraft(prev => ({ ...blankReceipt(dhakaToday()), shop: prev.shop, shopSub: prev.shopSub, note: prev.note }))
    setOrderQuery("")
    setLookup({ busy: false, message: null, isError: false })
  }

  return (
    <div className={FONT_VARS} style={{ padding: "1.75rem", maxWidth: "84rem" }}>
      <header style={{ display: "flex", flexWrap: "wrap", gap: "1rem", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.25rem" }}>
        <div>
          <Link href="/admin/store" style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", textDecoration: "none" }}>
            ← Store overview
          </Link>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em", marginTop: "0.35rem" }}>Receipts</h1>
          <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", marginTop: "0.25rem", maxWidth: "36rem" }}>
            A4 receipts for booklet printing. Type a walk-in job, or fill one from a store order. Your draft is kept in this browser.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" onClick={startNew} style={btn("secondary")}>New receipt</button>
          <button type="button" onClick={() => window.print()} style={btn("primary")}>Print on A4</button>
        </div>
      </header>

      <form
        onSubmit={e => { e.preventDefault(); void loadOrder(orderQuery) }}
        style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", marginBottom: "1.25rem" }}
      >
        <label htmlFor="gmr-order" style={{ fontSize: "0.78rem", color: "var(--gm-text-3)" }}>Fill from store order</label>
        <input id="gmr-order" className="gm-input" value={orderQuery} onChange={e => setOrderQuery(e.target.value)}
               placeholder="Order number" style={{ maxWidth: "14rem" }} />
        <button type="submit" disabled={lookup.busy || !orderQuery.trim()} style={btn("secondary")}>
          {lookup.busy ? "Looking up…" : "Fill in"}
        </button>
        {lookup.message ? (
          <span role="status" style={{ fontSize: "0.78rem", color: lookup.isError ? "#ef4444" : "var(--gm-text-2, var(--gm-text))" }}>
            {lookup.message}
          </span>
        ) : null}
      </form>

      <div className="gmr-layout">
        <ReceiptForm draft={draft} onChange={setDraft} />
        <div className="gmr-sheet-col">
          <p style={{ fontSize: "0.68rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gm-text-3)", marginBottom: "0.5rem" }}>
            A4 · 210 × 297 mm · print with margins set to none
          </p>
          <ReceiptSheet draft={draft} totals={totals} />
        </div>
      </div>

      {mounted
        ? createPortal(
            <div className={`gmr-print-root ${FONT_VARS}`} aria-hidden="true">
              <ReceiptSheet draft={draft} totals={totals} />
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}
