"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist"

/** Shipped in public/ and version-locked to the installed pdfjs-dist. */
const WORKER_SRC = "/pdf.worker.min.mjs"
/** Rasterise this far outside the viewport so scrolling stays ahead of the reader. */
const PRELOAD_MARGIN = "150% 0px"
/** Canvases further than this many pages from the nearest visible one are released. */
const KEEP_RADIUS = 3
/** Beyond 2x costs phone memory for no visible gain. */
const MAX_DPR = 2
const ZOOM_STEPS = [1, 1.5, 2, 3] as const

interface PageGeometry {
  /** Unscaled CSS width/height, used to size the placeholder before rasterising. */
  width: number
  height: number
}

let pdfjsPromise: Promise<typeof import("pdfjs-dist")> | null = null

/** Loaded on demand: pdf.js is ~350 KB and desktop never needs it. */
function loadPdfjs(): Promise<typeof import("pdfjs-dist")> {
  if (!pdfjsPromise) {
    pdfjsPromise = import("pdfjs-dist").then((lib) => {
      lib.GlobalWorkerOptions.workerSrc = WORKER_SRC
      return lib
    })
  }
  return pdfjsPromise
}

interface PdfCanvasViewerProps {
  url: string
  /** Used for the fallback link's wording, e.g. "Question Paper". */
  label: string
  /** Cleared while the split divider is dragged, so scrolling doesn't fight it. */
  interactive?: boolean
  onOpen?: () => void
}

/**
 * Scrollable, page-by-page PDF renderer for devices with no usable built-in
 * viewer. Pages are laid out at their true aspect ratio up front so the scroll
 * bar is honest, then rasterised lazily as they approach the viewport and
 * released again once they are well behind it — a 40-page mark scheme must not
 * hold 40 full-resolution canvases on a phone.
 */
export default function PdfCanvasViewer({
  url,
  label,
  interactive = true,
  onOpen,
}: PdfCanvasViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const pageRefs = useRef<(HTMLDivElement | null)[]>([])
  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([])
  const docRef = useRef<PDFDocumentProxy | null>(null)
  const taskRef = useRef<RenderTask | null>(null)
  /** Zoom/width at which each page index was last rasterised; null = blank. */
  const renderedAtRef = useRef<(number | null)[]>([])
  const queueRef = useRef<number[]>([])
  const renderingRef = useRef(false)

  const [geometry, setGeometry] = useState<PageGeometry[]>([])
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading")
  const [errorMessage, setErrorMessage] = useState("")
  const [zoomIndex, setZoomIndex] = useState(0)
  const [containerWidth, setContainerWidth] = useState(0)
  const [visiblePage, setVisiblePage] = useState(1)

  const zoom = ZOOM_STEPS[zoomIndex]
  const pageCount = geometry.length
  // Page box width in CSS pixels. Gutters keep the page off the frame edge.
  const renderWidth = useMemo(
    () => (containerWidth > 0 ? Math.max(180, (containerWidth - 16) * zoom) : 0),
    [containerWidth, zoom]
  )

  // ─── Load the document ──────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    setStatus("loading")
    setErrorMessage("")
    setGeometry([])
    renderedAtRef.current = []
    queueRef.current = []

    ;(async () => {
      try {
        const pdfjs = await loadPdfjs()
        // Ranged fetches: R2 answers 206, so a 40-page paper streams in as the
        // reader scrolls instead of downloading whole before the first page.
        const doc = await pdfjs.getDocument({ url, isEvalSupported: false }).promise
        if (cancelled) {
          void doc.destroy()
          return
        }
        docRef.current = doc

        const pages = await Promise.all(
          Array.from({ length: doc.numPages }, async (_, index) => {
            const page = await doc.getPage(index + 1)
            const viewport = page.getViewport({ scale: 1 })
            return { width: viewport.width, height: viewport.height }
          })
        )
        if (cancelled) return

        // Drop refs held for the previous document — a shorter paper would
        // otherwise leave dead canvases at the tail of the array.
        renderedAtRef.current = new Array<number | null>(pages.length).fill(null)
        pageRefs.current = new Array(pages.length).fill(null)
        canvasRefs.current = new Array(pages.length).fill(null)
        setGeometry(pages)
        setStatus("ready")
      } catch (error) {
        if (cancelled) return
        setErrorMessage(error instanceof Error ? error.message : "Unknown error")
        setStatus("error")
      }
    })()

    return () => {
      cancelled = true
      taskRef.current?.cancel()
      taskRef.current = null
      void docRef.current?.destroy()
      docRef.current = null
    }
  }, [url])

  // ─── Track the frame width ──────────────────────────────────────────────────
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      setContainerWidth(entry.contentRect.width)
    })
    observer.observe(element)
    setContainerWidth(element.clientWidth)
    return () => observer.disconnect()
  }, [status])

  // ─── Rasterise queued pages, one at a time ──────────────────────────────────
  const drainQueue = useCallback(async () => {
    if (renderingRef.current) return
    renderingRef.current = true
    try {
      while (queueRef.current.length > 0) {
        const index = queueRef.current.shift()
        const doc = docRef.current
        if (index === undefined || !doc) continue

        const canvas = canvasRefs.current[index]
        if (!canvas || renderedAtRef.current[index] === renderWidth) continue

        try {
          const page = await doc.getPage(index + 1)
          const base = page.getViewport({ scale: 1 })
          const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
          const viewport = page.getViewport({ scale: (renderWidth * dpr) / base.width })

          canvas.width = Math.round(viewport.width)
          canvas.height = Math.round(viewport.height)
          canvas.style.width = "100%"
          canvas.style.height = "auto"

          const context = canvas.getContext("2d")
          if (!context) continue

          const task = page.render({ canvas, canvasContext: context, viewport })
          taskRef.current = task
          await task.promise
          taskRef.current = null
          renderedAtRef.current[index] = renderWidth
        } catch {
          // A cancelled or failed page must not stall the rest of the document.
          taskRef.current = null
        }
      }
    } finally {
      renderingRef.current = false
    }
  }, [renderWidth])

  // ─── Queue pages as they approach the viewport, release the ones left behind ─
  useEffect(() => {
    if (status !== "ready" || pageCount === 0 || renderWidth === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const nowVisible: number[] = []
        for (const entry of entries) {
          const index = Number((entry.target as HTMLElement).dataset.pageIndex)
          if (!Number.isInteger(index)) continue
          if (entry.isIntersecting) nowVisible.push(index)
        }
        if (nowVisible.length === 0) return

        setVisiblePage(Math.min(...nowVisible) + 1)

        for (const index of nowVisible) {
          if (renderedAtRef.current[index] !== renderWidth && !queueRef.current.includes(index)) {
            queueRef.current.push(index)
          }
        }

        // Free canvases well outside the reading window.
        const lowest = Math.min(...nowVisible)
        const highest = Math.max(...nowVisible)
        for (let index = 0; index < pageCount; index += 1) {
          if (index >= lowest - KEEP_RADIUS && index <= highest + KEEP_RADIUS) continue
          if (renderedAtRef.current[index] === null) continue
          const canvas = canvasRefs.current[index]
          if (canvas) {
            canvas.width = 0
            canvas.height = 0
          }
          renderedAtRef.current[index] = null
        }

        void drainQueue()
      },
      { root: scrollRef.current, rootMargin: PRELOAD_MARGIN }
    )

    for (const element of pageRefs.current) {
      if (element) observer.observe(element)
    }
    return () => observer.disconnect()
  }, [status, pageCount, renderWidth, drainQueue])

  // Width or zoom changed — every canvas is now the wrong resolution.
  useEffect(() => {
    if (renderWidth === 0) return
    renderedAtRef.current = renderedAtRef.current.map(() => null)
    queueRef.current = []
  }, [renderWidth])

  const changeZoom = useCallback((delta: number) => {
    setZoomIndex((current) => Math.min(ZOOM_STEPS.length - 1, Math.max(0, current + delta)))
  }, [])

  if (status === "error") {
    return (
      <PaneFallback>
        <span style={{ display: "block", marginBottom: "0.75rem" }}>
          This {label.toLowerCase()} couldn&apos;t be rendered here{errorMessage ? ` (${errorMessage})` : ""}.
        </span>
        <OpenLink url={url} label={label} onOpen={onOpen} />
      </PaneFallback>
    )
  }

  return (
    <div
      style={{
        position: "relative",
        flex: 1,
        minHeight: 0,
        border: "1px solid var(--gm-border-2)",
        borderRadius: "0.75rem",
        overflow: "hidden",
        background: "var(--gm-surface-2)",
        pointerEvents: interactive ? "auto" : "none",
      }}
    >
      <div
        ref={scrollRef}
        style={{
          height: "100%",
          overflowY: "auto",
          overflowX: "auto",
          WebkitOverflowScrolling: "touch",
          padding: "0.5rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        {status === "loading" && <PaneSpinner />}

        {geometry.map((page, index) => (
          <div
            key={index}
            data-page-index={index}
            ref={(element) => {
              pageRefs.current[index] = element
            }}
            style={{
              width: renderWidth > 0 ? `${renderWidth}px` : "100%",
              // Reserve the real page height so the scrollbar is correct before
              // anything has been rasterised.
              aspectRatio: `${page.width} / ${page.height}`,
              flexShrink: 0,
              background: "#fff",
              borderRadius: "0.25rem",
              boxShadow: "0 1px 4px rgba(0,0,0,0.25)",
              overflow: "hidden",
            }}
          >
            <canvas
              ref={(element) => {
                canvasRefs.current[index] = element
              }}
              style={{ display: "block", width: "100%", height: "auto" }}
            />
          </div>
        ))}
      </div>

      {/* Floating controls — page position and zoom, out of the reading column. */}
      {status === "ready" && pageCount > 0 && (
        <div
          style={{
            position: "absolute",
            right: "0.6rem",
            bottom: "0.6rem",
            display: "flex",
            alignItems: "center",
            gap: "0.15rem",
            padding: "0.2rem 0.3rem",
            borderRadius: "99px",
            background: "var(--gm-nav-bg)",
            border: "1px solid var(--gm-border-2)",
            backdropFilter: "blur(10px)",
            WebkitBackdropFilter: "blur(10px)",
          }}
        >
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 600,
              color: "var(--gm-text-2)",
              padding: "0 0.4rem",
              whiteSpace: "nowrap",
            }}
          >
            {visiblePage} / {pageCount}
          </span>
          <ZoomButton label="Zoom out" disabled={zoomIndex === 0} onClick={() => changeZoom(-1)}>
            −
          </ZoomButton>
          <ZoomButton
            label="Zoom in"
            disabled={zoomIndex === ZOOM_STEPS.length - 1}
            onClick={() => changeZoom(1)}
          >
            +
          </ZoomButton>
        </div>
      )}
    </div>
  )
}

function ZoomButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string
  disabled: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: "1.7rem",
        height: "1.7rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "99px",
        border: "none",
        background: "transparent",
        color: disabled ? "var(--gm-text-3)" : "var(--gm-text)",
        opacity: disabled ? 0.4 : 1,
        fontSize: "1rem",
        lineHeight: 1,
        cursor: disabled ? "default" : "pointer",
      }}
    >
      {children}
    </button>
  )
}

function PaneSpinner() {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "12rem",
        color: "var(--gm-text-3)",
        fontSize: "0.8rem",
      }}
    >
      Loading pages…
    </div>
  )
}

function PaneFallback({ children }: { children: React.ReactNode }) {
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

function OpenLink({ url, label, onOpen }: { url: string; label: string; onOpen?: () => void }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onOpen}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.4rem",
        padding: "0.5rem 1rem",
        borderRadius: "0.5rem",
        fontSize: "0.8rem",
        fontWeight: 600,
        background: "var(--gm-blue-bg)",
        color: "var(--gm-blue)",
        border: "1px solid var(--gm-blue-ring)",
        textDecoration: "none",
      }}
    >
      Open the {label}
    </a>
  )
}
