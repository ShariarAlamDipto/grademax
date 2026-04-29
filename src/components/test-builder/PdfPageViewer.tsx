'use client';

import { useEffect, useRef, useState } from 'react';

let pdfjsCache: typeof import('pdfjs-dist') | null = null;
async function getPdfjsLib() {
  if (!pdfjsCache) {
    pdfjsCache = await import('pdfjs-dist');
    pdfjsCache.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
  }
  return pdfjsCache;
}

interface PdfPageViewerProps {
  url: string;
}

export default function PdfPageViewer({ url }: PdfPageViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const taskRef = useRef(0);

  useEffect(() => {
    if (!url) { setError(true); setLoading(false); return; }

    const gen = ++taskRef.current;
    setLoading(true);
    setError(false);

    (async () => {
      try {
        const pdfjsLib = await getPdfjsLib();
        const containerWidth = containerRef.current?.clientWidth || 400;
        const dpr = window.devicePixelRatio || 1;

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
        const scale = (containerWidth * dpr) / unscaledVp.width;
        const viewport = page.getViewport({ scale });

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = `${containerWidth}px`;
        canvas.style.height = `${(viewport.height / viewport.width) * containerWidth}px`;

        const ctx = canvas.getContext('2d');
        if (!ctx) { pdf.destroy(); return; }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await page.render({ canvasContext: ctx, viewport, canvas } as any).promise;
        pdf.destroy();

        if (gen === taskRef.current) setLoading(false);
      } catch (err) {
        console.warn('[PdfPageViewer] render failed:', url, err);
        if (gen === taskRef.current) { setError(true); setLoading(false); }
      }
    })();

    return () => { taskRef.current++; };
  }, [url]);

  return (
    <div ref={containerRef} className="w-full h-full overflow-y-auto bg-white">
      {loading && (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full" />
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-48 text-sm text-gray-500">
          Unable to load preview
        </div>
      )}
      <canvas ref={canvasRef} className={loading || error ? 'hidden' : 'block'} />
    </div>
  );
}
