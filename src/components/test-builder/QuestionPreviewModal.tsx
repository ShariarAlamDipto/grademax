'use client';

import { useState, useEffect } from 'react';
import PdfPageViewer from './PdfPageViewer';

interface QuestionPreviewModalProps {
  question: {
    id: string;
    questionNumber: string;
    topics: string[];
    difficulty: string;
    qpPageUrl: string;
    msPageUrl: string | null;
    year: number;
    season: string;
    paper: string;
    hasDiagram: boolean;
  };
  isInBasket: boolean;
  onAdd: () => void;
  onRemove: () => void;
  onClose: () => void;
}

export default function QuestionPreviewModal({
  question,
  isInBasket,
  onAdd,
  onRemove,
  onClose,
}: QuestionPreviewModalProps) {
  const [activeTab, setActiveTab] = useState<'qp' | 'ms'>('qp');
  const [isMobile, setIsMobile] = useState(false);
  const currentUrl = activeTab === 'ms' && question.msPageUrl ? question.msPageUrl : question.qpPageUrl;

  // Detect mobile on mount and on resize
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Desktop: Side panel from right
  if (!isMobile) {
    return (
      <>
        {/* Backdrop */}
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Side panel */}
        <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg bg-gray-900 border-l border-gray-700 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-700">
            <div className="min-w-0 flex-1">
              <h3 className="text-white font-bold text-base truncate">
                Q{question.questionNumber} — {question.year} {question.season} P{question.paper}
              </h3>
              <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                {question.topics.slice(0, 3).map((t) => (
                  <span key={t} className="text-[10px] px-1.5 py-0.5 bg-blue-900/50 text-blue-300 rounded font-mono">
                    {t}
                  </span>
                ))}
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  question.difficulty === 'easy' ? 'bg-emerald-900/50 text-emerald-300' :
                  question.difficulty === 'medium' ? 'bg-amber-900/50 text-amber-300' :
                  question.difficulty === 'hard' ? 'bg-red-900/50 text-red-300' :
                  'bg-gray-700 text-gray-300'
                }`}>
                  {question.difficulty || 'Unknown'}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="ml-3 p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Tab switcher */}
          {question.msPageUrl && (
            <div className="flex border-b border-gray-700">
              <button
                className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === 'qp'
                    ? 'text-green-400 border-b-2 border-green-400 bg-green-900/10'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
                onClick={() => setActiveTab('qp')}
              >
                Question Paper
              </button>
              <button
                className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === 'ms'
                    ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-900/10'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
                onClick={() => setActiveTab('ms')}
              >
                Mark Scheme
              </button>
            </div>
          )}

          {/* PDF preview via canvas — avoids mobile "Open" prompt */}
          <div className="flex-1 min-h-0 p-3 overflow-hidden">
            <div className="w-full h-full rounded-lg border border-gray-700 overflow-hidden">
              <PdfPageViewer key={currentUrl} url={currentUrl} />
            </div>
          </div>

          {/* Footer action */}
          <div className="p-4 border-t border-gray-700">
            {isInBasket ? (
              <button
                onClick={onRemove}
                className="w-full bg-red-500/20 text-red-400 hover:bg-red-500/30 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Remove from Test
              </button>
            ) : (
              <button
                onClick={onAdd}
                className="w-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                + Add to Test
              </button>
            )}
          </div>
        </div>
      </>
    );
  }

  // Mobile: Fullscreen modal
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
      />

      {/* Fullscreen modal */}
      <div className="fixed inset-0 z-50 bg-gray-900 flex flex-col">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between p-3 border-b border-gray-700 bg-gray-800">
          <div className="min-w-0 flex-1">
            <h3 className="text-white font-bold text-sm truncate">
              Q{question.questionNumber} — {question.year} {question.season} P{question.paper}
            </h3>
            <div className="flex items-center gap-1 mt-1 flex-wrap">
              {question.topics.slice(0, 2).map((t) => (
                <span key={t} className="text-[9px] px-1 py-0.5 bg-blue-900/50 text-blue-300 rounded font-mono">
                  {t}
                </span>
              ))}
              <span className={`text-[9px] px-1 py-0.5 rounded font-medium ${
                question.difficulty === 'easy' ? 'bg-emerald-900/50 text-emerald-300' :
                question.difficulty === 'medium' ? 'bg-amber-900/50 text-amber-300' :
                question.difficulty === 'hard' ? 'bg-red-900/50 text-red-300' :
                'bg-gray-700 text-gray-300'
              }`}>
                {question.difficulty || 'Unknown'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-2 p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors flex-shrink-0"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tab switcher */}
        {question.msPageUrl && (
          <div className="flex border-b border-gray-700 bg-gray-800">
            <button
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                activeTab === 'qp'
                  ? 'text-green-400 border-b-2 border-green-400 bg-green-900/10'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('qp')}
            >
              Question Paper
            </button>
            <button
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                activeTab === 'ms'
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-900/10'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('ms')}
            >
              Mark Scheme
            </button>
          </div>
        )}

        {/* PDF preview via canvas — avoids mobile "Open" prompt */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <PdfPageViewer key={currentUrl} url={currentUrl} />
        </div>

        {/* Footer actions */}
        <div className="shrink-0 p-3 border-t border-gray-700 bg-gray-800 flex gap-2">
          {isInBasket ? (
            <button
              onClick={onRemove}
              className="flex-1 bg-red-500/20 text-red-400 hover:bg-red-500/30 py-2 rounded-lg text-xs font-semibold transition-colors"
            >
              Remove from Test
            </button>
          ) : (
            <button
              onClick={onAdd}
              className="flex-1 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 py-2 rounded-lg text-xs font-semibold transition-colors"
            >
              + Add to Test
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 bg-gray-600/40 text-gray-300 hover:bg-gray-600/60 py-2 rounded-lg text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
}
