'use client';

import { useEffect, useRef, useState } from 'react';

// Cache the pdfjs module so it's only loaded once across all thumbnails
let pdfjsCache: typeof import('pdfjs-dist') | null = null;
async function getPdfjsLib() {
  if (!pdfjsCache) {
    pdfjsCache = await import('pdfjs-dist');
    pdfjsCache.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
  }
  return pdfjsCache;
}

interface PdfThumbnailProps {
  url: string;
  width?: number;
  className?: string;
  onClick?: () => void;
}

/**
 * Renders the first page of a PDF as a canvas thumbnail.
 * Worker is served from /public/pdf.worker.min.mjs for reliability.
 */
export default function PdfThumbnail({ url, width = 280, className = '', onClick }: PdfThumbnailProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const taskRef = useRef(0); // generation counter to cancel stale renders

  useEffect(() => {
    if (!url) { setError(true); setLoading(false); return; }

    const gen = ++taskRef.current;
    setLoading(true);
    setError(false);

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
        if (gen !== taskRef.current) { pdf.destroy(); return; }

        const page = await pdf.getPage(1);
        if (gen !== taskRef.current) { pdf.destroy(); return; }

        const canvas = canvasRef.current;
        if (!canvas) { pdf.destroy(); return; }

        const unscaledVp = page.getViewport({ scale: 1 });
        const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
        const scale = (width * dpr) / unscaledVp.width;
        const viewport = page.getViewport({ scale });

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${(viewport.height / viewport.width) * width}px`;

        const ctx = canvas.getContext('2d');
        if (!ctx) { pdf.destroy(); return; }

        const renderTask = page.render({
          canvasContext: ctx,
          viewport,
          canvas,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any);

        await renderTask.promise;
        pdf.destroy();

        if (gen === taskRef.current) setLoading(false);
      } catch (err) {
        console.warn('[PdfThumbnail] render failed:', url, err);
        if (gen === taskRef.current) { setError(true); setLoading(false); }
      }
    })();

    return () => { taskRef.current++; };
  }, [url, width]);

  if (error) {
    // Fallback: show the PDF in a scaled iframe
    return (
      <div
        className={`relative bg-white rounded-lg overflow-hidden ${onClick ? 'cursor-pointer' : ''} ${className}`}
        onClick={onClick}
        style={{ width, height: width * 1.414 }}
      >
        <iframe
          src={`${url}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
          className="border-0 pointer-events-none"
          title="PDF preview"
          style={{
            width: width * 3,
            height: width * 1.414 * 3,
            transform: 'scale(0.333)',
            transformOrigin: 'top left',
          }}
        />
      </div>
    );
  }

  return (
    <div
      className={`relative bg-white rounded-lg overflow-hidden ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
      style={{ width, minHeight: loading ? width * 1.414 : undefined }}
    >
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50" style={{ height: width * 1.414 }}>
          <div className="animate-spin w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full" />
        </div>
      )}
      <canvas ref={canvasRef} className={loading ? 'invisible absolute' : 'block'} />
    </div>
  );
}
