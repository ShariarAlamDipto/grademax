'use client';

import { useEffect, useRef, useState } from 'react';

/** Beyond 2x costs phone memory for no visible gain (iOS caps total canvas memory). */
const MAX_DPR = 2;
/** Start loading a little before the thumbnail scrolls into view. */
const PRELOAD_MARGIN = '300px 0px';
const A4_RATIO = 1.414;

// Cache the pdfjs module so it's only loaded once across all thumbnails
let pdfjsPromise: Promise<typeof import('pdfjs-dist')> | null = null;
function getPdfjsLib(): Promise<typeof import('pdfjs-dist')> {
  if (!pdfjsPromise) {
    pdfjsPromise = import('pdfjs-dist').then((lib) => {
      lib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
      return lib;
    });
  }
  return pdfjsPromise;
}

interface PdfThumbnailProps {
  url: string;
  /** Upper bound on the rendered width in CSS px; the thumbnail never exceeds its container. */
  width?: number;
  className?: string;
  onClick?: () => void;
}

/**
 * Renders the first page of a PDF as a canvas thumbnail.
 *
 * Fluid: it fills its container up to `width`, so a 400px thumbnail in a
 * 330px phone card is scaled down rather than cropped. Lazy: nothing is
 * fetched until it nears the viewport, so a page of 20 cards doesn't hold 20
 * full-resolution canvases at once. There is deliberately no <iframe>
 * fallback — phones paint a PDF iframe as a blank white box.
 */
export default function PdfThumbnail({ url, width = 280, className = '', onClick }: PdfThumbnailProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const taskRef = useRef(0); // generation counter to cancel stale renders

  useEffect(() => {
    const element = wrapperRef.current;
    if (!element) return;
    if (typeof IntersectionObserver === 'undefined') { setVisible(true); return; }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setVisible(true);
        observer.disconnect();
      }
    }, { rootMargin: PRELOAD_MARGIN });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!url) { setError(true); setLoading(false); return; }
    if (!visible) return;

    const gen = ++taskRef.current;
    setLoading(true);
    setError(false);

    (async () => {
      try {
        const pdfjsLib = await getPdfjsLib();

        // pdf.js can't stream a blob: URL, so read its bytes up front.
        const source = url.startsWith('blob:')
          ? { data: new Uint8Array(await (await fetch(url)).arrayBuffer()) }
          : { url };

        const pdf = await pdfjsLib.getDocument({
          ...source,
          disableAutoFetch: true,
          disableStream: true,
          isEvalSupported: false,
        }).promise;
        if (gen !== taskRef.current) { pdf.destroy(); return; }

        const page = await pdf.getPage(1);
        const canvas = canvasRef.current;
        if (gen !== taskRef.current || !canvas) { pdf.destroy(); return; }

        const cssWidth = Math.min(width, wrapperRef.current?.clientWidth || width);
        const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
        const unscaledVp = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: (cssWidth * dpr) / unscaledVp.width });

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const ctx = canvas.getContext('2d');
        if (!ctx) { pdf.destroy(); return; }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await page.render({ canvasContext: ctx, viewport, canvas } as any).promise;
        pdf.destroy();

        if (gen === taskRef.current) setLoading(false);
      } catch (err) {
        console.warn('[PdfThumbnail] render failed:', url, err);
        if (gen === taskRef.current) { setError(true); setLoading(false); }
      }
    })();

    return () => { taskRef.current++; };
  }, [url, width, visible]);

  return (
    <div
      ref={wrapperRef}
      className={`relative bg-white rounded-lg overflow-hidden ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
      style={{
        width: '100%',
        maxWidth: width,
        aspectRatio: loading || error ? `1 / ${A4_RATIO}` : undefined,
      }}
    >
      {loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
          <div className="animate-spin w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full" />
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50 px-3 text-center text-xs text-gray-500">
          Preview unavailable
        </div>
      )}
      <canvas
        ref={canvasRef}
        className={loading || error ? 'invisible absolute' : 'block'}
        style={{ width: '100%', height: 'auto' }}
      />
    </div>
  );
}
