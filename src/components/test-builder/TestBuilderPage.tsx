'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import SubjectSelector from './SubjectSelector';
import TopicTree from './TopicTree';
import FilterBar from './FilterBar';
import QuestionCard, { QuestionItem } from './QuestionCard';
import PaperPreview from './PaperPreview';
import QuestionPreviewModal from './QuestionPreviewModal';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface Subject {
  id: string;
  code: string;
  name: string;
  level?: string;
  board?: string;
}

interface Topic {
  id: string;
  code: string;
  name: string;
  description?: string;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

interface TestBuilderPageProps {
  initialSubjects: Subject[];
  initialTopics: Topic[];
}

// ─────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────

export default function TestBuilderPage({ initialSubjects, initialTopics }: TestBuilderPageProps) {
  // ── Subject & Topic State ──
  const [selectedSubject, setSelectedSubject] = useState<string>(initialSubjects[0]?.id || '');
  const [topics, setTopics] = useState<Topic[]>(initialTopics);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const topicsCache = useRef<Record<string, Topic[]>>({ [initialSubjects[0]?.id || '']: initialTopics });

  // ── Filters ──
  const [difficulty, setDifficulty] = useState('');
  const [yearStart, setYearStart] = useState(2011);
  const [yearEnd, setYearEnd] = useState(2025);

  // ── Question Browser ──
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [pagination, setPagination] = useState<Pagination>({ page: 1, limit: 20, total: 0, totalPages: 0 });
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [searchTriggered, setSearchTriggered] = useState(false);

  // ── Test Basket ──
  const [basketItems, setBasketItems] = useState<QuestionItem[]>([]);
  const [testTitle, setTestTitle] = useState('');

  // ── Preview ──
  const [previewQuestion, setPreviewQuestion] = useState<QuestionItem | null>(null);
  const [showMobilePreview, setShowMobilePreview] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // ── PDF Generation ──
  const [generating, setGenerating] = useState(false);
  const [worksheetUrl, setWorksheetUrl] = useState<string | null>(null);
  const [markschemeUrl, setMarkschemeUrl] = useState<string | null>(null);
  const [pdfProgress, setPdfProgress] = useState<{ step: number; total: number; label: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── Basket helpers ──
  const basketIds = useMemo(() => new Set(basketItems.map(i => i.id)), [basketItems]);

  // ─────────────────────────────────────────────
  // Fetch topics when subject changes
  // ─────────────────────────────────────────────

  useEffect(() => {
    if (!selectedSubject) return;
    if (topicsCache.current[selectedSubject]) {
      setTopics(topicsCache.current[selectedSubject]);
      return;
    }
    async function fetchTopics() {
      setLoadingTopics(true);
      try {
        const res = await fetch(`/api/topics?subjectId=${selectedSubject}`);
        const data = await res.json();
        if (Array.isArray(data)) {
          topicsCache.current[selectedSubject] = data;
          setTopics(data);
        } else {
          setTopics([]);
        }
      } catch {
        setTopics([]);
      } finally {
        setLoadingTopics(false);
      }
    }
    fetchTopics();
  }, [selectedSubject]);

  // Reset when subject changes — clear basket and any previously generated PDFs
  useEffect(() => {
    setSelectedTopics([]);
    setQuestions([]);
    setPagination({ page: 1, limit: 20, total: 0, totalPages: 0 });
    setSearchTriggered(false);
    setError(null);
    setBasketItems([]);
    setWorksheetUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setMarkschemeUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
  }, [selectedSubject]);

  // Detect mobile and auto-open drawer when first item added
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (isMobile && basketItems.length === 1) {
      setShowMobilePreview(true);
    }
  }, [basketItems, isMobile]);

  // ─────────────────────────────────────────────
  // Fetch questions
  // ─────────────────────────────────────────────

  const fetchQuestions = useCallback(async (page = 1) => {
    if (!selectedSubject) return;

    setLoadingQuestions(true);
    setError(null);
    setSearchTriggered(true);

    try {
      const params = new URLSearchParams();
      params.set('subjectId', selectedSubject);
      params.set('page', String(page));
      params.set('limit', '20');
      if (selectedTopics.length > 0) params.set('topics', selectedTopics.join(','));
      if (difficulty) params.set('difficulty', difficulty);
      if (yearStart) params.set('yearStart', String(yearStart));
      if (yearEnd) params.set('yearEnd', String(yearEnd));

      const res = await fetch(`/api/test-builder/questions?${params.toString()}`);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to fetch questions');
      }

      setQuestions(data.questions || []);
      setPagination(data.pagination || { page: 1, limit: 20, total: 0, totalPages: 0 });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch questions');
      setQuestions([]);
    } finally {
      setLoadingQuestions(false);
    }
  }, [selectedSubject, selectedTopics, difficulty, yearStart, yearEnd]);

  // ─────────────────────────────────────────────
  // Topic toggle
  // ─────────────────────────────────────────────

  const toggleTopic = (code: string) => {
    setSelectedTopics(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  // ─────────────────────────────────────────────
  // Basket operations
  // ─────────────────────────────────────────────

  const addToBasket = (q: QuestionItem) => {
    if (!basketIds.has(q.id)) {
      setBasketItems(prev => [...prev, q]);
    }
  };

  const removeFromBasket = (id: string) => {
    setBasketItems(prev => prev.filter(i => i.id !== id));
  };

  const moveUp = (index: number) => {
    if (index <= 0) return;
    setBasketItems(prev => {
      const arr = [...prev];
      [arr[index - 1], arr[index]] = [arr[index], arr[index - 1]];
      return arr;
    });
  };

  const moveDown = (index: number) => {
    setBasketItems(prev => {
      if (index >= prev.length - 1) return prev;
      const arr = [...prev];
      [arr[index], arr[index + 1]] = [arr[index + 1], arr[index]];
      return arr;
    });
  };

  const clearBasket = () => {
    // Revoke object URLs to prevent memory leaks
    if (worksheetUrl) URL.revokeObjectURL(worksheetUrl);
    if (markschemeUrl) URL.revokeObjectURL(markschemeUrl);

    setBasketItems([]);
    setWorksheetUrl(null);
    setMarkschemeUrl(null);
  };

  // ─────────────────────────────────────────────
  // Generate test PDF
  // ─────────────────────────────────────────────

  const handleGenerate = async () => {
    if (basketItems.length === 0) return;

    setGenerating(true);
    setError(null);

    // Revoke previous object URLs before creating new ones
    if (worksheetUrl) URL.revokeObjectURL(worksheetUrl);
    if (markschemeUrl) URL.revokeObjectURL(markschemeUrl);

    setWorksheetUrl(null);
    setMarkschemeUrl(null);

    const subject = initialSubjects.find(s => s.id === selectedSubject);
    const totalMarks = basketItems.length * 4;
    const pagesPayload = basketItems.map(item => ({
      qpPageUrl: item.qpPageUrl,
      msPageUrl: item.msPageUrl,
    }));

    try {
      // Step 1: Generate question paper PDF
      setPdfProgress({ step: 1, total: 3, label: 'Building question paper...' });
      const qpRes = await fetch('/api/test-builder/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: testTitle || 'Untitled Test',
          type: 'worksheet',
          totalMarks,
          subjectName: subject?.name || '',
          level: subject?.level || '',
          pages: pagesPayload,
        }),
      });

      if (!qpRes.ok) {
        const err = await qpRes.json().catch(() => ({ error: `Server error (${qpRes.status})` }));
        throw new Error(err.error || 'Failed to generate question paper');
      }
      const qpBlob = await qpRes.blob();
      setWorksheetUrl(URL.createObjectURL(qpBlob));

      // Step 2: Generate mark scheme PDF
      setPdfProgress({ step: 2, total: 3, label: 'Building mark scheme...' });
      const msRes = await fetch('/api/test-builder/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: testTitle || 'Untitled Test',
          type: 'markscheme',
          totalMarks,
          subjectName: subject?.name || '',
          level: subject?.level || '',
          pages: pagesPayload,
        }),
      });

      if (msRes.ok) {
        const msBlob = await msRes.blob();
        setMarkschemeUrl(URL.createObjectURL(msBlob));
      }

      // Step 3: Done
      setPdfProgress({ step: 3, total: 3, label: 'PDFs ready!' });
      setTimeout(() => setPdfProgress(null), 2000);

      // Background save — persist test to DB (non-blocking, failure doesn't affect the user)
      fetch('/api/test-builder/tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: testTitle || 'Untitled Test',
          subjectId: selectedSubject,
          items: basketItems.map((item, index) => ({
            pageId: item.id,
            sequenceOrder: index + 1,
          })),
        }),
      }).catch(() => {
        // Silent error — background save is non-critical
      });

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate PDF');
      setPdfProgress(null);
    } finally {
      setGenerating(false);
    }
  };

  // ─────────────────────────────────────────────
  // Download helpers
  // ─────────────────────────────────────────────

  const downloadFile = (url: string, filename: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // ─────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
      {/* Question Preview Side Panel */}
      {previewQuestion && (
        <QuestionPreviewModal
          question={previewQuestion}
          isInBasket={basketIds.has(previewQuestion.id)}
          onAdd={() => { addToBasket(previewQuestion); setPreviewQuestion(null); }}
          onRemove={() => { removeFromBasket(previewQuestion.id); setPreviewQuestion(null); }}
          onClose={() => setPreviewQuestion(null)}
        />
      )}

      <div className="max-w-[1800px] mx-auto p-4 md:p-6">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl md:text-4xl font-bold text-white mb-1">Test Builder</h1>
          <p className="text-gray-400 text-sm">
            Select topics, browse questions, and build your custom test paper with live preview
          </p>
        </div>

        {/* Subject Selection */}
        <div className="bg-gray-800/60 backdrop-blur-lg rounded-xl border border-gray-700 p-4 md:p-6 mb-6">
          <h2 className="text-lg font-bold text-white mb-4">Select Subject</h2>
          <SubjectSelector
            subjects={initialSubjects}
            selectedId={selectedSubject}
            onSelect={setSelectedSubject}
          />
        </div>

        {/* 3-Column Layout: Topics + Filters | Question Browser | Paper Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_380px] gap-4">
          
          {/* ═══ LEFT COLUMN: Topics + Filters ═══ */}
          <div className="space-y-4">
            <div className="bg-gray-800/60 backdrop-blur-lg rounded-xl border border-gray-700 p-4">
              <h2 className="text-base font-bold text-white mb-3">Topics</h2>
              <TopicTree
                topics={topics}
                selectedTopics={selectedTopics}
                onToggle={toggleTopic}
                onSelectAll={() => setSelectedTopics(topics.map(t => t.code))}
                onClearAll={() => setSelectedTopics([])}
                loading={loadingTopics}
              />
            </div>

            <div className="bg-gray-800/60 backdrop-blur-lg rounded-xl border border-gray-700 p-4">
              <FilterBar
                difficulty={difficulty}
                onDifficultyChange={setDifficulty}
                yearStart={yearStart}
                onYearStartChange={setYearStart}
                yearEnd={yearEnd}
                onYearEndChange={setYearEnd}
              />
            </div>

            <button
              onClick={() => fetchQuestions(1)}
              disabled={loadingQuestions}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-xl font-bold text-sm shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loadingQuestions ? 'Searching...' : 'Search Questions'}
            </button>
          </div>

          {/* ═══ CENTER COLUMN: Question Browser ═══ */}
          <div className="min-w-0">
            {error && (
              <div className="bg-red-900/60 border border-red-500/50 rounded-xl p-4 mb-4">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            {!searchTriggered && !loadingQuestions && (
              <div className="bg-gray-800/60 backdrop-blur-lg rounded-xl border border-gray-700 p-8 text-center">
                <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-300 mb-2">Browse Questions</h3>
                <p className="text-gray-500 text-sm max-w-md mx-auto">
                  Select topics and filters on the left, then click &quot;Search Questions&quot; to browse available questions.
                </p>
              </div>
            )}

            {loadingQuestions && (
              <div className="bg-gray-800/60 backdrop-blur-lg rounded-xl border border-gray-700 p-8 text-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-400 mx-auto mb-4"></div>
                <p className="text-gray-400 text-sm">Searching questions...</p>
              </div>
            )}

            {searchTriggered && !loadingQuestions && (
              <>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-bold text-white">
                    {pagination.total === 0 ? 'No questions found' : `${pagination.total} questions found`}
                  </h2>
                  {pagination.totalPages > 1 && (
                    <span className="text-xs text-gray-400">
                      Page {pagination.page} of {pagination.totalPages}
                    </span>
                  )}
                </div>

                {questions.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                    {questions.map((q) => (
                      <QuestionCard
                        key={q.id}
                        question={q}
                        isInBasket={basketIds.has(q.id)}
                        onAdd={addToBasket}
                        onRemove={removeFromBasket}
                        onPreview={setPreviewQuestion}
                      />
                    ))}
                  </div>
                )}

                {pagination.totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => fetchQuestions(pagination.page - 1)}
                      disabled={pagination.page <= 1}
                      className="px-4 py-2 text-sm bg-gray-800 border border-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Previous
                    </button>
                    {Array.from({ length: Math.min(pagination.totalPages, 7) }, (_, i) => {
                      let pageNum: number;
                      if (pagination.totalPages <= 7) {
                        pageNum = i + 1;
                      } else if (pagination.page <= 4) {
                        pageNum = i + 1;
                      } else if (pagination.page >= pagination.totalPages - 3) {
                        pageNum = pagination.totalPages - 6 + i;
                      } else {
                        pageNum = pagination.page - 3 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => fetchQuestions(pageNum)}
                          className={`w-9 h-9 text-sm rounded-lg transition-colors ${
                            pageNum === pagination.page
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-800 border border-gray-600 text-gray-300 hover:bg-gray-700'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => fetchQuestions(pagination.page + 1)}
                      disabled={pagination.page >= pagination.totalPages}
                      className="px-4 py-2 text-sm bg-gray-800 border border-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                    </button>
                  </div>
                )}

                {questions.length === 0 && pagination.total === 0 && (
                  <div className="bg-gray-800/40 rounded-xl p-8 text-center">
                    <p className="text-gray-400 text-sm">
                      No questions match your current filters. Try selecting different topics or adjusting filters.
                    </p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* ═══ RIGHT COLUMN: Live Paper Preview ═══ */}
          <div className="lg:sticky lg:top-24 lg:self-start lg:h-[calc(100vh-7rem)] lg:max-h-[calc(100vh-7rem)]">
            <PaperPreview
              items={basketItems}
              testTitle={testTitle}
              onTitleChange={setTestTitle}
              onRemove={removeFromBasket}
              onMoveUp={moveUp}
              onMoveDown={moveDown}
              onClearAll={clearBasket}
              onGenerate={handleGenerate}
              generating={generating}
              worksheetUrl={worksheetUrl}
              markschemeUrl={markschemeUrl}
              onDownloadQP={() => worksheetUrl && downloadFile(worksheetUrl, `${testTitle || 'test'}_question_paper.pdf`)}
              onDownloadMS={() => markschemeUrl && downloadFile(markschemeUrl, `${testTitle || 'test'}_mark_scheme.pdf`)}
              pdfProgress={pdfProgress}
              error={error}
            />
          </div>
        </div>

        {/* Mobile Preview Drawer Overlay */}
        {isMobile && showMobilePreview && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowMobilePreview(false)}
            />

            {/* Drawer Panel */}
            <div className="fixed bottom-0 left-0 right-0 top-[60px] z-40 bg-gradient-to-br from-gray-900 via-black to-gray-900 flex flex-col rounded-t-2xl overflow-hidden">
              {/* Header */}
              <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/80">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Preview ({basketItems.length})
                </h2>
                <button
                  onClick={() => setShowMobilePreview(false)}
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 min-h-0 overflow-hidden">
                <PaperPreview
                  items={basketItems}
                  testTitle={testTitle}
                  onTitleChange={setTestTitle}
                  onRemove={removeFromBasket}
                  onMoveUp={moveUp}
                  onMoveDown={moveDown}
                  onClearAll={clearBasket}
                  onGenerate={handleGenerate}
                  generating={generating}
                  worksheetUrl={worksheetUrl}
                  markschemeUrl={markschemeUrl}
                  onDownloadQP={() => worksheetUrl && downloadFile(worksheetUrl, `${testTitle || 'test'}_question_paper.pdf`)}
                  onDownloadMS={() => markschemeUrl && downloadFile(markschemeUrl, `${testTitle || 'test'}_mark_scheme.pdf`)}
                  pdfProgress={pdfProgress}
                  error={error}
                />
              </div>
            </div>
          </>
        )}

        {/* Mobile FAB Button */}
        {isMobile && basketItems.length > 0 && !showMobilePreview && (
          <button
            onClick={() => setShowMobilePreview(true)}
            className="fixed bottom-6 right-6 z-30 flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-full shadow-lg hover:shadow-xl transition-all active:scale-95 font-bold text-2xl"
            title="Show preview"
          >
            <div className="relative w-8 h-8">
              <svg className="absolute inset-0 w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <div className="absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full">
                {basketItems.length}
              </div>
            </div>
          </button>
        )}
      </div>
    </div>
  );
}
