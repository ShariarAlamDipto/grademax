'use client';

import { useEffect, useRef, useState } from 'react';

interface PdfThumbnailProps {
  url: string;
  width?: number;
  className?: string;
  onClick?: () => void;
}

/**
 * Renders the first page of a PDF as a canvas image.
 * Uses pdfjs-dist which is already installed.
 */
export default function PdfThumbnail({ url, width = 280, className = '', onClick }: PdfThumbnailProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const renderingRef = useRef(false);

  useEffect(() => {
    if (!url || renderingRef.current) return;
    renderingRef.current = true;
    setLoading(true);
    setError(false);

    let cancelled = false;

    (async () => {
      try {
        const pdfjsLib = await import('pdfjs-dist');
        // Use CDN worker to avoid Next.js bundling issues
        pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

        const loadingTask = pdfjsLib.getDocument({
          url,
          disableAutoFetch: true,
          disableStream: true,
        });
        const pdf = await loadingTask.promise;
        const page = await pdf.getPage(1);

        if (cancelled) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        // Scale to fit desired width
        const unscaledViewport = page.getViewport({ scale: 1 });
        const scale = (width * 2) / unscaledViewport.width; // 2x for retina
        const viewport = page.getViewport({ scale });

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${(viewport.height / viewport.width) * width}px`;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        await page.render({ canvas, canvasContext: ctx, viewport } as Parameters<typeof page.render>[0]).promise;
        if (!cancelled) setLoading(false);

        pdf.destroy();
      } catch {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      } finally {
        renderingRef.current = false;
      }
    })();

    return () => {
      cancelled = true;
      renderingRef.current = false;
    };
  }, [url, width]);

  return (
    <div
      className={`relative bg-white rounded-lg overflow-hidden ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
      style={{ width, minHeight: width * 1.4 }}
    >
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <div className="animate-pulse flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
            <span className="text-[10px] text-gray-400">Loading...</span>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <div className="text-center p-2">
            <svg className="w-6 h-6 text-gray-400 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="text-[10px] text-gray-400">Preview unavailable</span>
          </div>
        </div>
      )}
      <canvas ref={canvasRef} className={loading || error ? 'invisible' : ''} />
    </div>
  );
}
