"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import dynamic from "next/dynamic"
import { useCart } from "./useCart"
import { Badge, Button, Notice, Price, card } from "./StoreUI"
import { formatBdt } from "@/lib/store/format"
import type { PublicProduct, PublicVariant } from "@/lib/store/types"

/**
 * The preview renderer is heavy (pdf.js plus a worker), so it is only loaded
 * when a preview is actually opened — a product page must not pay for it.
 */
const MultiPagePdfPreview = dynamic(() => import("@/components/MultiPagePdfPreview"), {
  ssr: false,
  loading: () => (
    <p style={{ color: "var(--gm-text-3)", fontSize: "0.85rem", padding: "2rem 0", textAlign: "center" }}>
      Loading preview…
    </p>
  ),
})

interface Props {
  product: PublicProduct
  settings: { slaHours: number; deliveryMetro: number; deliveryOutside: number }
  /** Render the sample-pages block instead of the buy box. */
  showPreviewOnly?: boolean
}

export default function ProductBuyPanel({ product, settings, showPreviewOnly }: Props) {
  const router = useRouter()
  const { add, has } = useCart()

  const firstAvailable = product.variants.find(v => v.in_stock) ?? product.variants[0]
  const [selectedId, setSelectedId] = useState<string>(firstAvailable?.id ?? "")
  const [previewOpen, setPreviewOpen] = useState(false)
  const [added, setAdded] = useState(false)

  const selected = product.variants.find(v => v.id === selectedId) ?? firstAvailable

  if (showPreviewOnly) {
    if (!product.preview_url) return null
    return (
      <section style={{ ...card, marginBottom: "1.1rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Look inside</h2>
            <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>
              {product.preview_pages
                ? `The first ${product.preview_pages} pages, exactly as they are printed.`
                : "Sample pages, exactly as they are printed."}
            </p>
          </div>
          <Button variant="secondary" small onClick={() => setPreviewOpen(o => !o)}>
            {previewOpen ? "Hide preview" : "Open preview"}
          </Button>
        </div>

        {previewOpen ? (
          <div style={{
            marginTop: "1rem", borderTop: "1px solid var(--gm-border)", paddingTop: "1rem",
            maxHeight: "36rem", overflowY: "auto", borderRadius: "0.5rem",
          }}>
            <MultiPagePdfPreview url={product.preview_url} maxPages={product.preview_pages ?? 12} />
          </div>
        ) : null}
      </section>
    )
  }

  if (!selected) return null

  const outOfStock = !selected.in_stock
  const lowStock = selected.kind === "print" && selected.stock_qty !== null && selected.stock_qty > 0 && selected.stock_qty <= 5

  function handleAdd(thenCheckout: boolean) {
    if (!selected || outOfStock) return
    // A digital line is always quantity 1 — a second copy of the same file buys
    // the buyer nothing, and the server refuses it anyway.
    add(selected.id, 1, selected.kind === "digital")
    setAdded(true)
    if (thenCheckout) router.push("/checkout")
  }

  return (
    <aside style={{ ...card, position: "sticky", top: "5.5rem" }}>
      {/* With only one way to buy a title, a one-option picker is just noise. */}
      {product.variants.length > 1 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", marginBottom: "1rem" }}>
          {product.variants.map(v => (
            <VariantOption
              key={v.id}
              variant={v}
              selected={v.id === selectedId}
              onSelect={() => { setSelectedId(v.id); setAdded(false) }}
            />
          ))}
        </div>
      ) : (
        <p style={{ fontSize: "0.8rem", color: "var(--gm-text-2)", marginBottom: "0.9rem" }}>
          {selected.label}
        </p>
      )}

      <div style={{ paddingTop: "0.9rem", borderTop: "1px solid var(--gm-border)", marginBottom: "0.9rem" }}>
        <Price amount={selected.price_bdt} compareAt={selected.compare_at_bdt} />
        <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.35rem" }}>
          {selected.kind === "print"
            ? `Plus delivery — ${formatBdt(settings.deliveryMetro)} inside Dhaka, ${formatBdt(settings.deliveryOutside)} elsewhere.`
            : "No delivery charge. Download as soon as payment is confirmed."}
        </p>
      </div>

      {outOfStock ? (
        <Notice tone="red">
          This printed edition is out of stock right now.
          {product.variants.some(v => v.kind === "digital" && v.in_stock)
            ? " The PDF edition is still available above."
            : " Check back soon."}
        </Notice>
      ) : null}

      {lowStock ? (
        <Notice tone="amber">Only {selected.stock_qty} left in stock.</Notice>
      ) : null}

      {added && !outOfStock ? (
        <Notice tone="green">Added to your cart.</Notice>
      ) : null}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <Button full disabled={outOfStock} onClick={() => handleAdd(true)}>
          {outOfStock ? "Out of stock" : "Buy now"}
        </Button>
        <Button full variant="secondary" disabled={outOfStock} onClick={() => handleAdd(false)}>
          {has(selected.id) ? "In your cart — add another" : "Add to cart"}
        </Button>
      </div>

      <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.9rem", lineHeight: 1.6 }}>
        {selected.kind === "digital"
          ? `Pay with bKash or Nagad. We confirm payments within about ${settings.slaHours} hours, then your download unlocks.`
          : "Cash on delivery, or pay ahead with bKash or Nagad. You will need an account to order."}
      </p>
    </aside>
  )
}

function VariantOption({
  variant, selected, onSelect,
}: {
  variant: PublicVariant
  selected: boolean
  onSelect: () => void
}) {
  const disabled = !variant.in_stock
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem",
        width: "100%", textAlign: "left", cursor: disabled ? "not-allowed" : "pointer",
        padding: "0.7rem 0.8rem", borderRadius: "0.6rem",
        border: `1px solid ${selected ? "var(--gm-amber)" : "var(--gm-border-2)"}`,
        background: selected ? "var(--gm-amber-bg)" : "var(--gm-surface-2)",
        opacity: disabled ? 0.5 : 1,
        color: "var(--gm-text)",
      }}
    >
      <span style={{ minWidth: 0 }}>
        <span style={{ display: "block", fontSize: "0.85rem", fontWeight: 600 }}>
          {variant.kind === "print" ? "Printed copy" : "Digital PDF"}
        </span>
        <span style={{ display: "block", fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.1rem" }}>
          {variant.label}
        </span>
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: "0.45rem", flexShrink: 0 }}>
        {disabled ? <Badge tone="red">Sold out</Badge> : null}
        <strong style={{ fontSize: "0.9rem", fontWeight: 700 }}>{formatBdt(variant.price_bdt)}</strong>
      </span>
    </button>
  )
}
