'use client';

import { useEffect, useRef, useState } from 'react';
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PdfDocumentProxy = any;

/**
 * Multi-page canvas-based PDF preview.
 *
 * iOS Safari renders blob:application/pdf in iframes as a broken-page
 * icon, so we deliberately avoid <iframe> and rasterize each page onto
 * its own <canvas>. Pages are rendered sequentially to keep memory
 * pressure bounded — important on phones where iOS Safari can OOM the
 * tab if too many large canvases are alive simultaneously.
 */

let pdfjsCache: typeof import('pdfjs-dist') | null = null;
async function getPdfjsLib() {
  if (!pdfjsCache) {
    pdfjsCache = await import('pdfjs-dist');
    pdfjsCache.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
  }
  return pdfjsCache;
}

export interface MultiPagePdfPreviewProps {
  /** Blob URL or absolute URL to the PDF. */
  url: string;
  /** Hard cap on rendered pages — protects phones from OOM. */
  maxPages?: number;
  className?: string;
}

export default function MultiPagePdfPreview({
  url,
  maxPages = 30,
  className = '',
}: MultiPagePdfPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);
  const pdfRef = useRef<PdfDocumentProxy | null>(null);
  const generationRef = useRef(0);

  const [numPages, setNumPages] = useState(0);
  const [renderedCount, setRenderedCount] = useState(0);
  const [error, setError] = useState(false);
  const [totalPagesInDoc, setTotalPagesInDoc] = useState(0);

  // Phase 1: load the PDF and discover its page count.
  useEffect(() => {
    if (!url) {
      setError(true);
      return;
    }

    const gen = ++generationRef.current;
    setError(false);
    setNumPages(0);
    setRenderedCount(0);
    setTotalPagesInDoc(0);

    (async () => {
      try {
        const pdfjsLib = await getPdfjsLib();
        const loadingTask = pdfjsLib.getDocument({
          url,
          disableAutoFetch: true,
          disableStream: true,
          isEvalSupported: false,
        });
        const pdf = await loadingTask.promise;
        if (gen !== generationRef.current) {
          pdf.destroy();
          return;
        }
        pdfRef.current = pdf;
        setTotalPagesInDoc(pdf.numPages);
        setNumPages(Math.min(pdf.numPages, maxPages));
      } catch (err) {
        console.warn('[MultiPagePdfPreview] load failed:', err);
        if (gen === generationRef.current) setError(true);
      }
    })();

    return () => {
      // Bumping generationRef invalidates any in-flight async tasks; the
      // ref is mutated intentionally on cleanup, hence the lint suppression.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      generationRef.current++;
      const pdf = pdfRef.current;
      if (pdf) {
        pdf.destroy();
        pdfRef.current = null;
      }
    };
  }, [url, maxPages]);

  // Phase 2: once the page count is known and the canvases have mounted,
  // render each page in sequence. Sequential keeps memory bounded on
  // phones where parallel rendering can OOM the tab.
  useEffect(() => {
    const pdf = pdfRef.current;
    if (!pdf || numPages === 0) return;

    const gen = generationRef.current;
    let cancelled = false;
    const containerWidth = containerRef.current?.clientWidth || 400;
    const dpr = typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 2) : 1;

    (async () => {
      for (let i = 1; i <= numPages; i += 1) {
        if (cancelled || gen !== generationRef.current) return;
        const canvas = canvasRefs.current[i - 1];
        if (!canvas) continue;

        try {
          const page = await pdf.getPage(i);
          if (cancelled || gen !== generationRef.current) return;

          const unscaledVp = page.getViewport({ scale: 1 });
          const scale = (containerWidth * dpr) / unscaledVp.width;
          const viewport = page.getViewport({ scale });

          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.style.width = `${containerWidth}px`;
          canvas.style.height = `${(viewport.height / viewport.width) * containerWidth}px`;

          const ctx = canvas.getContext('2d');
          if (!ctx) continue;

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          await page.render({ canvasContext: ctx, viewport, canvas } as any).promise;
          if (!cancelled && gen === generationRef.current) {
            setRenderedCount((c) => c + 1);
          }
        } catch (err) {
          // A single failed page shouldn't kill the whole preview.
          console.warn('[MultiPagePdfPreview] page render failed', i, err);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [numPages]);

  if (error) {
    return (
      <div className={`flex items-center justify-center p-6 text-sm text-gray-500 bg-gray-100 rounded-lg ${className}`}>
        Unable to load preview
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`w-full bg-gray-100 rounded-lg p-2 space-y-2 ${className}`}>
      {numPages === 0 && (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full" />
        </div>
      )}
      {Array.from({ length: numPages }, (_, i) => (
        <div key={i} className="bg-white shadow rounded overflow-hidden">
          <canvas
            ref={(el) => {
              canvasRefs.current[i] = el;
            }}
            className="block w-full"
          />
        </div>
      ))}
      {totalPagesInDoc > maxPages && renderedCount >= numPages && (
        <p className="text-center text-xs text-gray-500 py-2">
          Showing first {maxPages} of {totalPagesInDoc} pages — open the full PDF for the rest.
        </p>
      )}
    </div>
  );
}
