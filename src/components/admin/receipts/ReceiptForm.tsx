"use client"

import { emptyItem, PAYMENT_METHODS, type ReceiptDraft, type ReceiptItem } from "@/lib/receipts/receiptMath"

/** The editor beside the A4 preview. Every change returns a new draft. */

type TextKey = "shop" | "shopSub" | "no" | "date" | "ready" | "cust" | "phone" | "addr" | "method" | "txn" | "note"
type AmountKey = "discount" | "delivery" | "paid"

const legendStyle: React.CSSProperties = {
  fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
  color: "var(--gm-blue)", marginBottom: "0.35rem", padding: 0,
}
const labelStyle: React.CSSProperties = { display: "grid", gap: "0.25rem", fontSize: "0.74rem", color: "var(--gm-text-3)", minWidth: 0 }
const fieldsetStyle: React.CSSProperties = { border: 0, margin: 0, padding: 0, display: "grid", gap: "0.75rem", minWidth: 0 }

export function btn(variant: "primary" | "secondary" | "ghost"): React.CSSProperties {
  const palette = {
    primary:   { background: "var(--gm-amber)", color: "#1a1206", border: "1px solid transparent" },
    secondary: { background: "var(--gm-surface-2)", color: "var(--gm-text)", border: "1px solid var(--gm-border-2)" },
    ghost:     { background: "transparent", color: "var(--gm-text-3)", border: "1px dashed var(--gm-border-2)" },
  }[variant]
  return { ...palette, padding: "0.45rem 0.85rem", borderRadius: "0.45rem", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer" }
}

interface Props {
  draft: ReceiptDraft
  onChange: (next: ReceiptDraft) => void
}

export default function ReceiptForm({ draft, onChange }: Props) {
  const text = (key: TextKey) => ({
    id: `gmr-${key}`,
    className: "gm-input",
    value: draft[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      onChange({ ...draft, [key]: e.target.value }),
  })
  const amount = (key: AmountKey) => ({
    id: `gmr-${key}`,
    className: "gm-input",
    type: "number",
    min: 0,
    step: 1,
    inputMode: "numeric" as const,
    value: draft[key] || "",
    placeholder: "0",
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...draft, [key]: Number(e.target.value) || 0 }),
  })

  const setItem = (index: number, patch: Partial<ReceiptItem>) =>
    onChange({ ...draft, items: draft.items.map((it, i) => (i === index ? { ...it, ...patch } : it)) })
  const removeItem = (index: number) => {
    const items = draft.items.filter((_, i) => i !== index)
    onChange({ ...draft, items: items.length ? items : [emptyItem()] })
  }

  return (
    <form className="gmr-form" onSubmit={e => e.preventDefault()} autoComplete="off" style={{
      background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem",
      padding: "1.25rem", display: "grid", gap: "1.35rem", minWidth: 0,
    }}>
      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>Shop</legend>
        <label style={labelStyle} htmlFor="gmr-shop">Business name<input {...text("shop")} /></label>
        <label style={labelStyle} htmlFor="gmr-shopSub">Address / contact line<input {...text("shopSub")} /></label>
      </fieldset>

      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>Customer</legend>
        <div className="gmr-row">
          <label style={labelStyle} htmlFor="gmr-no">Receipt no.<input {...text("no")} /></label>
          <label style={labelStyle} htmlFor="gmr-date">Date<input {...text("date")} type="date" /></label>
        </div>
        <div className="gmr-row">
          <label style={labelStyle} htmlFor="gmr-cust">Name<input {...text("cust")} /></label>
          <label style={labelStyle} htmlFor="gmr-phone">Phone<input {...text("phone")} inputMode="tel" /></label>
        </div>
        <div className="gmr-row">
          <label style={labelStyle} htmlFor="gmr-addr">Address / school<input {...text("addr")} /></label>
          <label style={labelStyle} htmlFor="gmr-ready">Ready / delivery by<input {...text("ready")} type="date" /></label>
        </div>
      </fieldset>

      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>Booklets</legend>
        {draft.items.map((it, i) => (
          <div className="gmr-item-row" key={i}>
            <label className="gmr-name-field" style={labelStyle} htmlFor={`gmr-it-name-${i}`}>
              Booklet
              <input id={`gmr-it-name-${i}`} className="gm-input" value={it.name} onChange={e => setItem(i, { name: e.target.value })} />
            </label>
            <button type="button" className="gmr-x" onClick={() => removeItem(i)} aria-label={`Remove booklet ${i + 1}`}
                    style={{ ...btn("secondary"), height: "2.25rem", padding: 0, fontSize: "1rem" }}>×</button>
            <label className="gmr-spec-field" style={labelStyle} htmlFor={`gmr-it-spec-${i}`}>
              Size · pages · binding
              <input id={`gmr-it-spec-${i}`} className="gm-input" value={it.spec} placeholder="A4 · 200 pp · spiral bound"
                     onChange={e => setItem(i, { spec: e.target.value })} />
            </label>
            <label className="gmr-qty-field" style={labelStyle} htmlFor={`gmr-it-qty-${i}`}>
              Copies
              <input id={`gmr-it-qty-${i}`} className="gm-input" type="number" min={0} step={1} inputMode="numeric"
                     value={it.qty || ""} onChange={e => setItem(i, { qty: Number(e.target.value) || 0 })} />
            </label>
            <label className="gmr-rate-field" style={labelStyle} htmlFor={`gmr-it-rate-${i}`}>
              Rate (৳)
              <input id={`gmr-it-rate-${i}`} className="gm-input" type="number" min={0} step={1} inputMode="numeric"
                     value={it.rate || ""} placeholder="0" onChange={e => setItem(i, { rate: Number(e.target.value) || 0 })} />
            </label>
          </div>
        ))}
        <button type="button" onClick={() => onChange({ ...draft, items: [...draft.items, emptyItem()] })}
                style={{ ...btn("ghost"), justifySelf: "start", color: "var(--gm-blue)" }}>
          + Add booklet
        </button>
      </fieldset>

      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>Charges &amp; payment</legend>
        <div className="gmr-row">
          <label style={labelStyle} htmlFor="gmr-discount">Discount (৳)<input {...amount("discount")} /></label>
          <label style={labelStyle} htmlFor="gmr-delivery">Delivery (৳)<input {...amount("delivery")} /></label>
        </div>
        <div className="gmr-row">
          <label style={labelStyle} htmlFor="gmr-paid">Advance paid (৳)<input {...amount("paid")} /></label>
          <label style={labelStyle} htmlFor="gmr-method">
            Payment method
            <select {...text("method")} className="gm-select">
              {PAYMENT_METHODS.map(m => <option key={m}>{m}</option>)}
            </select>
          </label>
        </div>
        <label style={labelStyle} htmlFor="gmr-txn">Transaction ID (optional)<input {...text("txn")} /></label>
      </fieldset>

      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>Note</legend>
        <label style={labelStyle} htmlFor="gmr-note">
          Printed in a box on the receipt
          <textarea {...text("note")} rows={3} style={{ resize: "vertical" }} />
        </label>
      </fieldset>
    </form>
  )
}
