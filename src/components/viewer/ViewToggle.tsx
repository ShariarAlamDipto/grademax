"use client"

import type { ViewerDoc, ViewerView } from "@/lib/viewer-link"

interface ViewToggleProps {
  doc: ViewerDoc
  view: ViewerView
  hasQp: boolean
  hasMs: boolean
  /** Side-by-side needs both PDFs and a wide enough viewport. */
  canSplit: boolean
  onSelectDoc: (doc: ViewerDoc) => void
  onSelectSplit: () => void
}

const SEGMENT_BASE: React.CSSProperties = {
  padding: "0.4rem 0.8rem",
  fontSize: "0.75rem",
  fontWeight: 600,
  background: "transparent",
  border: "none",
  cursor: "pointer",
  whiteSpace: "nowrap",
  transition: "background 0.15s, color 0.15s",
}

/** Question Paper / Mark Scheme / Side by side — one minimal segmented control. */
export default function ViewToggle({
  doc,
  view,
  hasQp,
  hasMs,
  canSplit,
  onSelectDoc,
  onSelectSplit,
}: ViewToggleProps) {
  const segments: { key: string; label: string; active: boolean; enabled: boolean; onClick: () => void }[] = [
    {
      key: "qp",
      label: "Question Paper",
      active: view === "single" && doc === "qp",
      enabled: hasQp,
      onClick: () => onSelectDoc("qp"),
    },
    {
      key: "ms",
      label: "Mark Scheme",
      active: view === "single" && doc === "ms",
      enabled: hasMs,
      onClick: () => onSelectDoc("ms"),
    },
    {
      key: "split",
      label: "Side by side",
      active: view === "split",
      enabled: canSplit,
      onClick: onSelectSplit,
    },
  ]

  return (
    <div
      role="group"
      aria-label="Document view"
      style={{
        display: "inline-flex",
        alignItems: "stretch",
        borderRadius: "0.6rem",
        border: "1px solid var(--gm-border-2)",
        background: "var(--gm-card-bg)",
        overflow: "hidden",
      }}
    >
      {segments.map((segment) => (
        <button
          key={segment.key}
          type="button"
          disabled={!segment.enabled}
          aria-pressed={segment.active}
          onClick={segment.onClick}
          // "Side by side" is hidden rather than disabled on narrow screens —
          // two PDFs in a phone-width column helps nobody.
          className={segment.key === "split" ? "gm-split-segment" : undefined}
          style={{
            ...SEGMENT_BASE,
            background: segment.active ? "var(--gm-blue-bg)" : "transparent",
            color: segment.active
              ? "var(--gm-blue)"
              : segment.enabled
                ? "var(--gm-text-2)"
                : "var(--gm-text-3)",
            cursor: segment.enabled ? "pointer" : "not-allowed",
            opacity: segment.enabled ? 1 : 0.45,
          }}
        >
          {segment.label}
        </button>
      ))}
    </div>
  )
}
