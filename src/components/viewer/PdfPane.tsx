"use client"

import dynamic from "next/dynamic"
import { usePdfRenderMode } from "./usePdfSupport"

// Only phones and tablets pull pdf.js down; desktop uses the browser's viewer.
const PdfCanvasViewer = dynamic(() => import("./PdfCanvasViewer"), { ssr: false })

interface PdfPaneProps {
  url: string | null
  /** "Question Paper" / "Mark Scheme" — shown in the pane strip and iframe title. */
  label: string
  /** Paper name, used for the iframe's accessible title. */
  title: string
  /** Shown above the frame. Off in single view, where the page header says it. */
  showLabel?: boolean
  /** Cleared while the split divider is being dragged so the frame stops eating pointer events. */
  interactive?: boolean
  onOpen?: () => void
}

/**
 * One PDF frame. Never renders a bare empty box: a browser that cannot show a
 * PDF inline, or a paper with no file of this kind, gets explanatory text and a
 * direct link instead.
 */
export default function PdfPane({
  url,
  label,
  title,
  showLabel = false,
  interactive = true,
  onOpen,
}: PdfPaneProps) {
  const renderMode = usePdfRenderMode()

  return (
    <div style={{ display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0, height: "100%" }}>
      {showLabel && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "0.5rem",
            padding: "0 0.15rem 0.4rem",
          }}
        >
          <span
            style={{
              fontSize: "0.62rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--gm-text-3)",
            }}
          >
            {label}
          </span>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={onOpen}
              style={{ fontSize: "0.68rem", color: "var(--gm-text-3)", textDecoration: "none" }}
              className="gm-link"
            >
              Open ↗
            </a>
          )}
        </div>
      )}

      {!url ? (
        <PaneMessage>{label} is not available for this paper.</PaneMessage>
      ) : renderMode === null ? (
        // One frame while we work out which renderer this device needs. Holding
        // off avoids starting a PDF download we are about to abandon.
        <PaneMessage>Loading…</PaneMessage>
      ) : renderMode === "canvas" ? (
        <PdfCanvasViewer url={url} label={label} interactive={interactive} onOpen={onOpen} />
      ) : (
        <iframe
          key={url}
          src={url}
          title={`${title} – ${label}`}
          style={{
            flex: 1,
            width: "100%",
            minHeight: 0,
            border: "1px solid var(--gm-border-2)",
            borderRadius: "0.75rem",
            background: "#fff",
            pointerEvents: interactive ? "auto" : "none",
          }}
        />
      )}
    </div>
  )
}

function PaneMessage({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "2rem 1.5rem",
        minHeight: "12rem",
        border: "1px solid var(--gm-border-2)",
        borderRadius: "0.75rem",
        background: "var(--gm-card-bg)",
        color: "var(--gm-text-3)",
        fontSize: "0.85rem",
      }}
    >
      {children}
    </div>
  )
}
