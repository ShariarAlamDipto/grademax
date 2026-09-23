"use client"

import { useEffect, useState } from "react"

/**
 * "native" — hand the PDF to the browser's own viewer in an `<iframe>`. Best on
 * desktop: real text selection, search, print and page navigation for free.
 *
 * "canvas" — rasterise the pages ourselves with pdf.js. Required on phones and
 * tablets, where an `<iframe>` pointed at a PDF paints an empty white box (or a
 * broken-page icon on iOS Safari) and the paper looks missing.
 *
 * `null` until the first effect runs, so the server HTML and first client paint
 * agree and no PDF is fetched down a path we're about to throw away.
 */
export type PdfRenderMode = "native" | "canvas" | null

export function usePdfRenderMode(): PdfRenderMode {
  const [mode, setMode] = useState<PdfRenderMode>(null)

  useEffect(() => {
    // The standard signal (Chrome 94+, Safari 16.4+, Firefox 88+). Android
    // Chrome reports false outright.
    const enabled = (navigator as Navigator & { pdfViewerEnabled?: boolean }).pdfViewerEnabled
    if (enabled === false) {
      setMode("canvas")
      return
    }

    // iOS/iPadOS Safari reports the flag as true but still refuses to scroll a
    // PDF inside a frame, so touch devices always get the canvas renderer.
    const touch = window.matchMedia("(pointer: coarse)").matches
    setMode(touch ? "canvas" : "native")
  }, [])

  return mode
}
