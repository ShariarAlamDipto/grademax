"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { track } from "@vercel/analytics"
import PdfPane from "@/components/viewer/PdfPane"
import ViewToggle from "@/components/viewer/ViewToggle"
import type { ViewerDoc, ViewerView } from "@/lib/viewer-link"

const DOC_LABELS: Record<ViewerDoc, string> = {
  qp: "Question Paper",
  ms: "Mark Scheme",
}

/** Below this the two panes would be too narrow to read, so split is withdrawn. */
const SPLIT_MIN_WIDTH = 1024
const VIEW_STORAGE_KEY = "gm.viewer.view"
const SPLIT_STORAGE_KEY = "gm.viewer.split-pct"
const MIN_PCT = 25
const MAX_PCT = 75

interface ViewerClientProps {
  qpUrl: string | null
  msUrl: string | null
  title: string
  backPath: string
  requestedDoc: ViewerDoc
  requestedView: ViewerView
}

export default function ViewerClient({
  qpUrl,
  msUrl,
  title,
  backPath,
  requestedDoc,
  requestedView,
}: ViewerClientProps) {
  // Server and client compute the same initial state from the same props, so the
  // first paint already shows the right PDF (no hydration mismatch).
  const initialDoc: ViewerDoc =
    requestedDoc === "ms" ? (msUrl ? "ms" : "qp") : qpUrl ? "qp" : "ms"
  const [doc, setDoc] = useState<ViewerDoc>(initialDoc)
  const [view, setView] = useState<ViewerView>(requestedView)
  const [splitPct, setSplitPct] = useState(50)
  const [dragging, setDragging] = useState(false)
  const panesRef = useRef<HTMLDivElement>(null)

  const bothAvailable = Boolean(qpUrl && msUrl)
  const activeUrl = doc === "ms" ? msUrl : qpUrl

  // Remembered preferences. Read after mount so the server HTML stays valid;
  // an explicit ?view= in the link always wins over the stored default.
  useEffect(() => {
    try {
      const storedPct = Number(window.localStorage.getItem(SPLIT_STORAGE_KEY))
      if (Number.isFinite(storedPct) && storedPct >= MIN_PCT && storedPct <= MAX_PCT) {
        setSplitPct(storedPct)
      }
      if (requestedView === "single" && bothAvailable) {
        if (window.localStorage.getItem(VIEW_STORAGE_KEY) === "split") setView("split")
      }
    } catch {
      // Private mode / blocked storage — the defaults are already correct.
    }
  }, [requestedView, bothAvailable])

  // Withdraw split on narrow viewports (and on rotate/resize into one).
  useEffect(() => {
    const query = window.matchMedia(`(min-width: ${SPLIT_MIN_WIDTH}px)`)
    const apply = () => {
      if (!query.matches) setView("single")
    }
    apply()
    query.addEventListener("change", apply)
    return () => query.removeEventListener("change", apply)
  }, [])

  // Keep the URL shareable without pushing history entries for a UI toggle.
  useEffect(() => {
    const url = new URL(window.location.href)
    if (view === "split") url.searchParams.set("view", "split")
    else url.searchParams.delete("view")
    url.searchParams.set("doc", doc)
    window.history.replaceState(null, "", `${url.pathname}${url.search}`)
  }, [view, doc])

  useEffect(() => {
    if (view === "split" && bothAvailable) track("pdf_view", { doc: "split", paper: title })
    else if (activeUrl) track("pdf_view", { doc, paper: title })
  }, [view, doc, activeUrl, bothAvailable, title])

  const persist = useCallback((key: string, value: string) => {
    try {
      window.localStorage.setItem(key, value)
    } catch {
      // Storage unavailable — the preference just won't survive this session.
    }
  }, [])

  const selectDoc = useCallback(
    (next: ViewerDoc) => {
      setDoc(next)
      setView("single")
      persist(VIEW_STORAGE_KEY, "single")
    },
    [persist]
  )

  const selectSplit = useCallback(() => {
    setView("split")
    persist(VIEW_STORAGE_KEY, "split")
  }, [persist])

  const onDividerMove = useCallback((clientX: number) => {
    const rect = panesRef.current?.getBoundingClientRect()
    if (!rect || rect.width === 0) return
    const pct = ((clientX - rect.left) / rect.width) * 100
    setSplitPct(Math.min(MAX_PCT, Math.max(MIN_PCT, pct)))
  }, [])

  const endDrag = useCallback(() => {
    setDragging(false)
    persist(SPLIT_STORAGE_KEY, String(Math.round(splitPct)))
  }, [persist, splitPct])

  // Tracked on the window, not the container: the cursor routinely travels over
  // the PDF frames (and past the container edge) mid-drag, and releasing outside
  // the window would otherwise leave the divider stuck to the cursor.
  useEffect(() => {
    if (!dragging) return
    const onMove = (event: PointerEvent) => onDividerMove(event.clientX)
    window.addEventListener("pointermove", onMove)
    window.addEventListener("pointerup", endDrag)
    window.addEventListener("pointercancel", endDrag)
    return () => {
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("pointerup", endDrag)
      window.removeEventListener("pointercancel", endDrag)
    }
  }, [dragging, endDrag, onDividerMove])

  if (!qpUrl && !msUrl) {
    return (
      <main
        style={{
          minHeight: "60vh",
          background: "var(--gm-bg)",
          color: "var(--gm-text)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "3rem 1.5rem",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "28rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.75rem" }}>Paper not found</h1>
          <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
            This viewer link is missing or invalid. Browse all past papers to find the one you need.
          </p>
          <Link
            href="/past-papers"
            style={{
              display: "inline-flex",
              padding: "0.6rem 1.1rem",
              borderRadius: "0.6rem",
              background: "var(--gm-blue-bg)",
              color: "var(--gm-blue)",
              border: "1px solid var(--gm-blue-ring)",
              fontSize: "0.85rem",
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            Browse Past Papers
          </Link>
        </div>
      </main>
    )
  }

  const isSplit = view === "split" && bothAvailable
  const headerLabel = isSplit ? "Question Paper & Mark Scheme" : DOC_LABELS[doc]

  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <div style={{ maxWidth: "112rem", margin: "0 auto", padding: "1rem 1rem 1.5rem" }}>
        {/* Header: back link + title + controls */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: "0.75rem",
            flexWrap: "wrap",
            marginBottom: "0.75rem",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <Link href={backPath} className="gm-link" style={{ fontSize: "0.72rem" }}>
              ← Back to paper page
            </Link>
            <h1
              style={{
                fontSize: "1rem",
                fontWeight: 700,
                margin: "0.15rem 0 0",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {title} <span style={{ color: "var(--gm-text-3)", fontWeight: 500 }}>· {headerLabel}</span>
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <ViewToggle
              doc={doc}
              view={view}
              hasQp={Boolean(qpUrl)}
              hasMs={Boolean(msUrl)}
              canSplit={bothAvailable}
              onSelectDoc={selectDoc}
              onSelectSplit={selectSplit}
            />

            {!isSplit && activeUrl && (
              <a
                href={activeUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => track("pdf_download", { doc, paper: title })}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.4rem 0.8rem",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  borderRadius: "0.6rem",
                  border: "1px solid var(--gm-border-2)",
                  color: "var(--gm-text-2)",
                  textDecoration: "none",
                }}
              >
                <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Download
              </a>
            )}
          </div>
        </div>

        {/* Frames */}
        <div
          ref={panesRef}
          style={{
            display: isSplit ? "grid" : "block",
            gridTemplateColumns: isSplit ? `${splitPct}% 0.75rem 1fr` : undefined,
            height: "clamp(30rem, calc(100vh - 11rem), 64rem)",
            userSelect: dragging ? "none" : undefined,
          }}
        >
          {isSplit ? (
            <>
              <PdfPane
                url={qpUrl}
                label={DOC_LABELS.qp}
                title={title}
                showLabel
                interactive={!dragging}
                onOpen={() => track("pdf_download", { doc: "qp", paper: title })}
              />

              <div
                role="separator"
                aria-label="Resize panes"
                aria-orientation="vertical"
                onPointerDown={(event) => {
                  event.preventDefault()
                  setDragging(true)
                }}
                style={{
                  cursor: "col-resize",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  touchAction: "none",
                }}
              >
                <span
                  style={{
                    width: "2px",
                    height: "2.5rem",
                    borderRadius: "2px",
                    background: dragging ? "var(--gm-blue)" : "var(--gm-border-input)",
                  }}
                />
              </div>

              <PdfPane
                url={msUrl}
                label={DOC_LABELS.ms}
                title={title}
                showLabel
                interactive={!dragging}
                onOpen={() => track("pdf_download", { doc: "ms", paper: title })}
              />
            </>
          ) : (
            <PdfPane
              url={activeUrl}
              label={DOC_LABELS[doc]}
              title={title}
              onOpen={() => track("pdf_download", { doc, paper: title })}
            />
          )}
        </div>

        {activeUrl && (
          <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.7rem" }}>
            PDF not loading?{" "}
            <a href={activeUrl} target="_blank" rel="noopener noreferrer" className="gm-link">
              Open it directly
            </a>
            {isSplit && msUrl && (
              <>
                {" · "}
                <a href={msUrl} target="_blank" rel="noopener noreferrer" className="gm-link">
                  Open the mark scheme
                </a>
              </>
            )}
          </p>
        )}
      </div>
    </main>
  )
}
