'use client';

import { QuestionItem } from './QuestionCard';
import PdfThumbnail from './PdfThumbnail';

interface PaperPreviewProps {
  items: QuestionItem[];
  testTitle: string;
  onRemove: (id: string) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onClearAll: () => void;
  onGenerate: () => void;
  generating: boolean;
  onTitleChange: (title: string) => void;
  worksheetUrl: string | null;
  markschemeUrl: string | null;
  onDownloadQP: () => void;
  onDownloadMS: () => void;
  pdfProgress: { step: number; total: number; label: string } | null;
  error?: string | null;
}

/** A4 aspect ratio: 210 × 297 mm ≈ 1 : 1.4142 */
const A4_RATIO = 297 / 210;

export default function PaperPreview({
  items,
  testTitle,
  onRemove,
  onMoveUp,
  onMoveDown,
  onClearAll,
  onGenerate,
  generating,
  onTitleChange,
  worksheetUrl,
  markschemeUrl,
  onDownloadQP,
  onDownloadMS,
  pdfProgress,
  error,
}: PaperPreviewProps) {
  const totalMarks = items.length * 4;

  return (
    <div className="bg-gray-800/80 border border-gray-700 rounded-xl flex flex-col h-full overflow-hidden">
      {/* ── Header ── */}
      <div className="shrink-0 p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Paper Preview
          </h2>
          {items.length > 0 && (
            <button onClick={onClearAll} className="text-xs text-red-400 hover:text-red-300 transition-colors">
              Clear All
            </button>
          )}
        </div>
        <input
          type="text"
          value={testTitle}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Test title..."
          className="w-full px-3 py-2 text-sm bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        {items.length > 0 && (
          <div className="flex justify-between text-xs mt-2 text-gray-400">
            <span>{items.length} question{items.length !== 1 ? 's' : ''} · {items.length + 1} pages</span>
            <span>~{totalMarks} marks</span>
          </div>
        )}
      </div>

      {/* ── Scrollable paper pages ── */}
      <div className="flex-1 overflow-y-auto min-h-0 p-3">
        {items.length === 0 ? (
          <div className="text-center py-12 px-4">
            <svg className="w-12 h-12 text-gray-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <p className="text-sm text-gray-500 font-medium">No questions added</p>
            <p className="text-xs text-gray-600 mt-1">
              Browse questions on the left and add them to build your test paper
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* ── Page 1: Cover Page (A4 ratio) ── */}
            <div className="relative">
              <span className="absolute -top-0 left-2 z-10 bg-gray-700 text-gray-300 text-[9px] font-bold px-1.5 py-0.5 rounded-b">
                COVER PAGE
              </span>
              <div
                className="bg-white rounded-lg shadow-md border border-gray-300 flex items-center justify-center overflow-hidden"
                style={{ aspectRatio: `1 / ${A4_RATIO}` }}
              >
                <div className="text-center px-6 w-full" style={{ fontFamily: 'Times New Roman, serif' }}>
                  <p className="text-[10px] text-gray-400 tracking-[0.2em] uppercase mb-4">Question Paper</p>
                  <p className="text-sm font-bold text-gray-900 mb-5 leading-tight">{testTitle || 'Untitled Test'}</p>
                  <div className="mx-auto max-w-[160px] space-y-2.5 text-left text-[10px]">
                    <div className="flex items-end gap-1">
                      <span className="text-gray-500 shrink-0">Name</span>
                      <span className="flex-1 border-b border-gray-300" />
                    </div>
                    <div className="flex items-end gap-1">
                      <span className="text-gray-500 shrink-0">Total Marks</span>
                      <span className="font-bold text-gray-800 ml-auto">{totalMarks}</span>
                    </div>
                    <div className="flex items-end gap-1">
                      <span className="text-gray-500 shrink-0">Marks Received</span>
                      <span className="flex-1 border-b border-gray-300" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Question Pages (each in A4 ratio) ── */}
            {items.map((item, index) => (
              <div key={item.id} className="relative group">
                <span className="absolute -top-0 left-2 z-10 bg-black/70 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-b">
                  Q{index + 1}
                </span>

                {/* Reorder & remove controls */}
                <div className="absolute top-1.5 right-2 z-10 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => onMoveUp(index)} disabled={index === 0}
                    className="p-1 bg-gray-900/80 text-white rounded hover:bg-gray-800 disabled:opacity-30" title="Move up">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7" /></svg>
                  </button>
                  <button onClick={() => onMoveDown(index)} disabled={index === items.length - 1}
                    className="p-1 bg-gray-900/80 text-white rounded hover:bg-gray-800 disabled:opacity-30" title="Move down">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                  </button>
                  <button onClick={() => onRemove(item.id)}
                    className="p-1 bg-red-600/80 text-white rounded hover:bg-red-700" title="Remove">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>

                <div
                  className="bg-white rounded-lg shadow-md border border-gray-300 overflow-hidden"
                  style={{ aspectRatio: `1 / ${A4_RATIO}` }}
                >
                  <PdfThumbnail url={item.qpPageUrl} width={340} className="w-full h-full object-contain" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Footer — always visible ── */}
      <div className="shrink-0 p-4 border-t border-gray-700 space-y-2">
        {error && (
          <div className="bg-red-900/50 border border-red-500/40 rounded-lg p-2 mb-1">
            <p className="text-red-300 text-xs">{error}</p>
          </div>
        )}

        {pdfProgress && (
          <div className="mb-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-white">{pdfProgress.label}</span>
              <span className="text-[10px] text-gray-400">{pdfProgress.step}/{pdfProgress.total}</span>
            </div>
            <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.round((pdfProgress.step / pdfProgress.total) * 100)}%`,
                  background: pdfProgress.step === pdfProgress.total
                    ? 'linear-gradient(to right, #22c55e, #10b981)' : 'linear-gradient(to right, #3b82f6, #6366f1)' }} />
            </div>
          </div>
        )}

        {/* Download buttons — shown after generate succeeds */}
        {(worksheetUrl || markschemeUrl) && (
          <div className="flex gap-2">
            {worksheetUrl && (
              <button onClick={onDownloadQP}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2.5 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Question Paper
              </button>
            )}
            {markschemeUrl && (
              <button onClick={onDownloadMS}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Mark Scheme
              </button>
            )}
          </div>
        )}

        <button onClick={onGenerate} disabled={items.length === 0 || generating}
          className="w-full bg-gradient-to-r from-emerald-500 to-green-600 text-white py-2.5 rounded-xl font-bold text-sm shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed">
          {generating ? 'Generating...' : worksheetUrl ? 'Regenerate PDF' : 'Generate & Download PDF'}
        </button>
      </div>
    </div>
  );
}
