"use client"

import Link from "next/link"
import { useCallback, useEffect, useState } from "react"

/**
 * Prices, stock, and the switch that puts a product on sale — plus the store
 * settings the checkout depends on.
 *
 * Putting a product on sale is refused by the server when it cannot actually be
 * delivered: no price, or a digital variant whose PDF is not in the private
 * bucket. The reason comes back as a sentence and is shown as-is.
 */

interface Variant {
  id: string
  kind: "print" | "digital"
  label: string
  price_bdt: number
  stock_qty: number | null
  is_active: boolean
  page_count: number | null
  files: { id: string; label: string; file_name: string; file_bytes: number | null }[]
}

interface Product {
  id: string
  slug: string
  title: string
  subtitle: string | null
  subject_code: string | null
  spec_summary: string | null
  preview_r2_key: string | null
  preview_pages: number | null
  is_active: boolean
  sort_order: number
  store_variants: Variant[]
}

interface Setting {
  key: string
  value: string
  description: string | null
}

export default function StoreProducts() {
  const [products, setProducts] = useState<Product[]>([])
  const [settings, setSettings] = useState<Setting[]>([])
  const [bucketOk, setBucketOk] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [p, s] = await Promise.all([
        fetch("/api/admin/store/products").then(r => r.json()),
        fetch("/api/admin/store/settings").then(r => r.json()),
      ])
      setProducts(p.products ?? [])
      setBucketOk(p.storeBucketConfigured !== false)
      setSettings(s.settings ?? [])
    } catch {
      setMessage("Could not load the catalogue.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function patch(body: unknown) {
    setMessage(null)
    const res = await fetch("/api/admin/store/products", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    const json = await res.json()
    setMessage(json.error ?? "Saved.")
    if (res.ok) await load()
  }

  return (
    <div style={{ padding: "1.75rem", maxWidth: "70rem" }}>
      <header style={{ marginBottom: "1.25rem" }}>
        <Link href="/admin/store" style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", textDecoration: "none" }}>
          ← Store overview
        </Link>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em", marginTop: "0.35rem" }}>
          Products &amp; prices
        </h1>
      </header>

      {!bucketOk ? (
        <Callout tone="red">
          <strong>Digital downloads are not deliverable yet.</strong> The environment variable{" "}
          <code>R2_STORE_BUCKET</code> is not set, so there is no private bucket to serve paid PDFs
          from. Paid files must never go in the papers bucket — it is public. Until this is set, you
          can still sell printed copies.
        </Callout>
      ) : null}

      {message ? <Callout tone="neutral">{message}</Callout> : null}
      {loading ? <p style={{ color: "var(--gm-text-3)", fontSize: "0.85rem" }}>Loading…</p> : null}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", marginBottom: "2rem" }}>
        {products.map(product => (
          <ProductCard key={product.id} product={product} onPatch={patch} />
        ))}
      </div>

      <SettingsPanel settings={settings} onSaved={load} />
    </div>
  )
}

function ProductCard({ product, onPatch }: { product: Product; onPatch: (body: unknown) => Promise<void> }) {
  return (
    <section style={{
      background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)",
      borderRadius: "0.65rem", padding: "1rem",
      opacity: product.is_active ? 1 : 0.85,
    }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap", marginBottom: "0.9rem" }}>
        <div style={{ minWidth: 0 }}>
          <h2 style={{ fontSize: "0.95rem", fontWeight: 700 }}>{product.title}</h2>
          <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.15rem" }}>
            {product.subject_code ? `${product.subject_code} · ` : ""}{product.spec_summary ?? product.subtitle ?? ""}
          </p>
          <p style={{ fontSize: "0.68rem", color: "var(--gm-text-3)", marginTop: "0.25rem" }}>
            {product.preview_r2_key
              ? `Preview: ${product.preview_pages ?? "?"} pages uploaded`
              : "No preview uploaded"}
          </p>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: "0.45rem", cursor: "pointer", flexShrink: 0 }}>
          <input
            type="checkbox"
            className="gm-checkbox"
            checked={product.is_active}
            onChange={e => onPatch({ product: { productId: product.id, isActive: e.target.checked } })}
          />
          <span style={{ fontSize: "0.78rem", fontWeight: 600, color: product.is_active ? "var(--gm-green)" : "var(--gm-text-3)" }}>
            {product.is_active ? "On sale" : "Hidden"}
          </span>
        </label>
      </header>

      <div style={{ display: "grid", gap: "0.6rem" }}>
        {product.store_variants.map(v => (
          <VariantRow key={v.id} variant={v} onPatch={onPatch} />
        ))}
      </div>
    </section>
  )
}

function VariantRow({ variant, onPatch }: { variant: Variant; onPatch: (body: unknown) => Promise<void> }) {
  const [price, setPrice] = useState(String(variant.price_bdt))
  const [stock, setStock] = useState(variant.stock_qty === null ? "" : String(variant.stock_qty))
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    setPrice(String(variant.price_bdt))
    setStock(variant.stock_qty === null ? "" : String(variant.stock_qty))
    setDirty(false)
  }, [variant.price_bdt, variant.stock_qty])

  const missingFiles = variant.kind === "digital" && variant.files.length === 0
  const unpriced = variant.price_bdt <= 0

  return (
    <div style={{
      display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto auto auto auto",
      gap: "0.6rem", alignItems: "center",
      background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)",
      borderRadius: "0.5rem", padding: "0.6rem 0.75rem",
    }}>
      <span style={{ minWidth: 0 }}>
        <strong style={{ fontSize: "0.8rem", fontWeight: 700, display: "block" }}>
          {variant.kind === "print" ? "Printed copy" : "Digital PDF"}
        </strong>
        <span style={{ fontSize: "0.68rem", color: "var(--gm-text-3)" }}>
          {missingFiles ? "No files uploaded — cannot be delivered" : variant.label}
          {unpriced ? " · price not set" : ""}
        </span>
      </span>

      <label style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
        <span style={{ fontSize: "0.68rem", color: "var(--gm-text-3)" }}>৳</span>
        <input
          className="gm-input" value={price} inputMode="numeric"
          onChange={e => { setPrice(e.target.value.replace(/\D/g, "")); setDirty(true) }}
          style={{ width: "5.5rem", padding: "0.3rem 0.45rem", fontSize: "0.8rem" }}
        />
      </label>

      {variant.kind === "print" ? (
        <label style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span style={{ fontSize: "0.68rem", color: "var(--gm-text-3)" }}>stock</span>
          <input
            className="gm-input" value={stock} inputMode="numeric"
            onChange={e => { setStock(e.target.value.replace(/\D/g, "")); setDirty(true) }}
            style={{ width: "4.5rem", padding: "0.3rem 0.45rem", fontSize: "0.8rem" }}
          />
        </label>
      ) : (
        <span style={{ fontSize: "0.68rem", color: "var(--gm-text-3)" }}>unlimited</span>
      )}

      <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer" }}>
        <input
          type="checkbox" className="gm-checkbox" checked={variant.is_active}
          onChange={e => onPatch({ variant: { variantId: variant.id, isActive: e.target.checked } })}
        />
        <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>sell</span>
      </label>

      <button
        disabled={!dirty}
        onClick={() => onPatch({
          variant: {
            variantId: variant.id,
            priceBdt: Number(price || 0),
            ...(variant.kind === "print" ? { stockQty: Number(stock || 0) } : {}),
          },
        })}
        style={{
          padding: "0.35rem 0.7rem", borderRadius: "0.4rem", fontSize: "0.72rem", fontWeight: 600,
          cursor: dirty ? "pointer" : "not-allowed", opacity: dirty ? 1 : 0.4,
          background: "var(--gm-amber)", color: "#1a1206", border: "none",
        }}
      >
        Save
      </button>
    </div>
  )
}

function SettingsPanel({ settings, onSaved }: { settings: Setting[]; onSaved: () => void }) {
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setDraft(Object.fromEntries(settings.map(s => [s.key, s.value])))
  }, [settings])

  async function save() {
    setBusy(true)
    setMessage(null)
    try {
      const res = await fetch("/api/admin/store/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates: draft }),
      })
      const json = await res.json()
      setMessage(json.error ?? "Settings saved.")
      if (res.ok) onSaved()
    } catch {
      setMessage("Could not save the settings.")
    } finally {
      setBusy(false)
    }
  }

  const enabled = (draft.store_enabled ?? "").toLowerCase() === "true"

  return (
    <section style={{
      background: "var(--gm-card-bg)", border: "1px solid var(--gm-border)",
      borderRadius: "0.65rem", padding: "1rem",
    }}>
      <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.9rem" }}>Store settings</h2>

      {message ? <Callout tone="neutral">{message}</Callout> : null}

      <label style={{
        display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer",
        background: enabled ? "var(--gm-green-bg)" : "var(--gm-surface-2)",
        border: `1px solid ${enabled ? "var(--gm-green)" : "var(--gm-border-2)"}`,
        borderRadius: "0.5rem", padding: "0.7rem 0.85rem", marginBottom: "1rem",
      }}>
        <input
          type="checkbox" className="gm-checkbox" checked={enabled}
          onChange={e => setDraft(d => ({ ...d, store_enabled: e.target.checked ? "true" : "false" }))}
        />
        <span>
          <strong style={{ fontSize: "0.82rem", display: "block" }}>
            {enabled ? "The shop is open" : "The shop is closed"}
          </strong>
          <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)" }}>
            When closed, /store shows a holding message and checkout is refused.
          </span>
        </span>
      </label>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 16rem), 1fr))", gap: "0.75rem" }}>
        {settings
          .filter(s => s.key !== "store_enabled")
          .map(s => (
            <label key={s.key} style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: "0.72rem", fontWeight: 600, color: "var(--gm-text-2)", marginBottom: "0.25rem" }}>
                {s.key.replace(/_/g, " ")}
              </span>
              {s.key === "payment_instructions" ? (
                <textarea
                  className="gm-input" rows={2} value={draft[s.key] ?? ""}
                  onChange={e => setDraft(d => ({ ...d, [s.key]: e.target.value }))}
                  style={{ resize: "vertical" }}
                />
              ) : (
                <input
                  className="gm-input" value={draft[s.key] ?? ""}
                  onChange={e => setDraft(d => ({ ...d, [s.key]: e.target.value }))}
                />
              )}
              {s.description ? (
                <span style={{ display: "block", fontSize: "0.66rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>
                  {s.description}
                </span>
              ) : null}
            </label>
          ))}
      </div>

      <button onClick={save} disabled={busy} style={{
        marginTop: "1rem", padding: "0.5rem 1rem", borderRadius: "0.45rem",
        background: "var(--gm-amber)", color: "#1a1206", border: "none",
        fontSize: "0.8rem", fontWeight: 700, cursor: busy ? "not-allowed" : "pointer",
      }}>
        {busy ? "Saving…" : "Save settings"}
      </button>
    </section>
  )
}

function Callout({ tone, children }: { tone: "red" | "neutral"; children: React.ReactNode }) {
  const c = tone === "red"
    ? { bg: "#ef444418", border: "#ef4444" }
    : { bg: "var(--gm-surface-2)", border: "var(--gm-border-2)" }
  return (
    <div style={{
      background: c.bg, border: `1px solid ${c.border}`, borderRadius: "0.5rem",
      padding: "0.7rem 0.85rem", fontSize: "0.8rem", lineHeight: 1.6, marginBottom: "1rem",
    }}>
      {children}
    </div>
  )
}
