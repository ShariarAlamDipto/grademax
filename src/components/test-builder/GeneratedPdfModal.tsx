'use client';

import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import PdfCanvasViewer from '@/components/viewer/PdfCanvasViewer';

interface GeneratedPdfModalProps {
  url: string;
  /** e.g. "Question Paper" — shown in the header and the viewer's fallback link. */
  label: string;
  onClose: () => void;
}

/**
 * Full-screen, in-page view of a freshly generated PDF for touch devices.
 *
 * Phones can't use the new-tab preview: iOS navigates the whole page to the
 * blob: URL (the basket only survives via sessionStorage), and in-app
 * browsers (Instagram, Facebook, Gmail) block blob: navigation outright, so
 * the tap did nothing. Rendering with pdf.js here keeps the student on the page.
 *
 * Portalled to <body>: it is opened from inside the mobile drawer (z-40) and
 * the sticky desktop column, which are their own stacking contexts — inside
 * them no z-index can lift it above the fixed navbar, which covered Close.
 */
export default function GeneratedPdfModal({ url, label, onClose }: GeneratedPdfModalProps) {
  // Lock the page behind the modal so scrolling the PDF doesn't scroll it too.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, []);

  return createPortal(
    <div className="fixed inset-0 z-[60] bg-gray-900 flex flex-col" role="dialog" aria-modal="true" aria-label={label}>
      <div className="shrink-0 flex items-center justify-between px-4 py-3 pt-[calc(0.75rem+env(safe-area-inset-top))] border-b border-gray-700 bg-gray-800">
        <h2 className="text-base font-bold text-white">{label}</h2>
        <button
          onClick={onClose}
          className="px-3 py-1.5 text-sm font-semibold text-gray-200 bg-gray-700 hover:bg-gray-600 rounded-lg"
        >
          Close
        </button>
      </div>
      <div className="flex-1 min-h-0 flex flex-col p-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))]">
        <PdfCanvasViewer url={url} label={label} />
      </div>
    </div>,
    document.body,
  );
}
