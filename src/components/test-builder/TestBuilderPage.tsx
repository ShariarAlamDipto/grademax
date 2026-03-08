'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import SubjectSelector from './SubjectSelector';
import TopicTree from './TopicTree';
import FilterBar from './FilterBar';
import QuestionCard, { QuestionItem } from './QuestionCard';
import TestBasket from './TestBasket';
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
// Fullscreen PDF modal (shared)
// ─────────────────────────────────────────────

function FullscreenPdfModal({ url, title, onClose }: { url: string; title: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-95 flex flex-col">
      <div className="flex items-center justify-between p-3 md:p-4 bg-gray-900 border-b border-gray-700">
        <h3 className="text-white font-semibold text-sm md:text-lg truncate">{title}</h3>
        <button
          onClick={onClose}
          className="text-white bg-red-600 hover:bg-red-700 px-3 py-1.5 md:px-4 md:py-2 rounded-lg font-semibold text-sm transition-colors"
        >
          Close
        </button>
      </div>
      <div className="flex-1 p-2 md:p-4">
        <iframe src={url} className="w-full h-full border-0 rounded-lg bg-white" title={title} />
      </div>
    </div>
  );
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
  
  // ── PDF Generation ──
  const [generating, setGenerating] = useState(false);
  const [worksheetUrl, setWorksheetUrl] = useState<string | null>(null);
  const [markschemeUrl, setMarkschemeUrl] = useState<string | null>(null);
  const [fullscreenPdf, setFullscreenPdf] = useState<{ url: string; title: string } | null>(null);
  const [pdfProgress, setPdfProgress] = useState<{ step: number; total: number; label: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── Basket helpers ──
  const basketIds = new Set(basketItems.map(i => i.id));

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

  // Reset when subject changes
  useEffect(() => {
    setSelectedTopics([]);
    setQuestions([]);
    setPagination({ page: 1, limit: 20, total: 0, totalPages: 0 });
    setSearchTriggered(false);
    setError(null);
  }, [selectedSubject]);

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
    setBasketItems([]);
  };

  // ─────────────────────────────────────────────
  // Generate test PDF
  // ─────────────────────────────────────────────

  const handleGenerate = async () => {
    if (basketItems.length === 0) return;

    setGenerating(true);
    setError(null);
    setWorksheetUrl(null);
    setMarkschemeUrl(null);

    try {
      // Step 1: Create test record
      setPdfProgress({ step: 1, total: 4, label: 'Creating test...' });
      const createRes = await fetch('/api/test-builder/tests', {
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
      });

      const createData = await createRes.json();
      if (!createRes.ok) {
        throw new Error(createData.error || 'Failed to create test');
      }

      const testId = createData.test.id;

      // Step 2: Download question paper PDF
      setPdfProgress({ step: 2, total: 4, label: 'Building question paper PDF...' });
      const qpRes = await fetch(`/api/test-builder/tests/${testId}/download?type=worksheet`);
      if (!qpRes.ok) {
        const err = await qpRes.json();
        throw new Error(err.error || 'Failed to generate question paper');
      }
      const qpBlob = await qpRes.blob();
      const qpUrl = URL.createObjectURL(qpBlob);
      setWorksheetUrl(qpUrl);

      // Step 3: Download mark scheme PDF
      setPdfProgress({ step: 3, total: 4, label: 'Building mark scheme PDF...' });
      const msRes = await fetch(`/api/test-builder/tests/${testId}/download?type=markscheme`);
      if (msRes.ok) {
        const msBlob = await msRes.blob();
        const msUrl = URL.createObjectURL(msBlob);
        setMarkschemeUrl(msUrl);
      }

      // Step 4: Done
      setPdfProgress({ step: 4, total: 4, label: 'PDFs ready!' });
      setTimeout(() => setPdfProgress(null), 2000);

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate test');
      setPdfProgress(null);
    } finally {
      setGenerating(false);
    }
  };

  // ─────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
      {/* Fullscreen PDF Modal */}
      {fullscreenPdf && (
        <FullscreenPdfModal
          url={fullscreenPdf.url}
          title={fullscreenPdf.title}
          onClose={() => setFullscreenPdf(null)}
        />
      )}

      {/* Question Preview Modal */}
      {previewQuestion && (
        <QuestionPreviewModal
          question={previewQuestion}
          isInBasket={basketIds.has(previewQuestion.id)}
          onAdd={() => { addToBasket(previewQuestion); setPreviewQuestion(null); }}
          onRemove={() => { removeFromBasket(previewQuestion.id); setPreviewQuestion(null); }}
          onClose={() => setPreviewQuestion(null)}
        />
      )}

      <div className="max-w-[1600px] mx-auto p-4 md:p-6">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl md:text-4xl font-bold text-white mb-1">Test Builder</h1>
          <p className="text-gray-400 text-sm">
            Select topics, browse individual questions, and build your custom test paper
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

        {/* 3-Column Layout: Topics + Filters | Question Browser | Test Basket */}
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_300px] gap-4">
          
          {/* ═══ LEFT COLUMN: Topics + Filters ═══ */}
          <div className="space-y-4">
            {/* Topic Tree */}
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

            {/* Filters */}
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

            {/* Search Button */}
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
            {/* Error */}
            {error && (
              <div className="bg-red-900/60 border border-red-500/50 rounded-xl p-4 mb-4">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            {/* Not searched yet */}
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

            {/* Loading */}
            {loadingQuestions && (
              <div className="bg-gray-800/60 backdrop-blur-lg rounded-xl border border-gray-700 p-8 text-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-400 mx-auto mb-4"></div>
                <p className="text-gray-400 text-sm">Searching questions...</p>
              </div>
            )}

            {/* Results */}
            {searchTriggered && !loadingQuestions && (
              <>
                {/* Results header */}
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

                {/* Question grid */}
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

                {/* Pagination */}
                {pagination.totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => fetchQuestions(pagination.page - 1)}
                      disabled={pagination.page <= 1}
                      className="px-4 py-2 text-sm bg-gray-800 border border-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Previous
                    </button>
                    {/* Page number buttons */}
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

                {/* No results message */}
                {questions.length === 0 && pagination.total === 0 && (
                  <div className="bg-gray-800/40 rounded-xl p-8 text-center">
                    <p className="text-gray-400 text-sm">
                      No questions match your current filters. Try selecting different topics or adjusting filters.
                    </p>
                  </div>
                )}
              </>
            )}

            {/* ══ Generated PDFs section ══ */}
            {(worksheetUrl || markschemeUrl) && (
              <div className="mt-6 bg-gradient-to-r from-green-900/40 to-emerald-900/40 border-2 border-green-500/50 rounded-xl p-4 md:p-6">
                <h3 className="font-bold text-green-300 mb-3 text-lg">Test PDFs Ready!</h3>
                <div className="flex flex-col sm:flex-row gap-3 mb-4">
                  {worksheetUrl && (
                    <a
                      href={worksheetUrl}
                      download={`${testTitle || 'test'}_question_paper.pdf`}
                      className="flex-1 bg-gray-700 border-2 border-green-500 text-green-300 px-6 py-3 rounded-lg font-semibold hover:bg-green-900/50 transition-colors text-center text-sm"
                    >
                      Download Question Paper
                    </a>
                  )}
                  {markschemeUrl && (
                    <a
                      href={markschemeUrl}
                      download={`${testTitle || 'test'}_mark_scheme.pdf`}
                      className="flex-1 bg-gray-700 border-2 border-blue-500 text-blue-300 px-6 py-3 rounded-lg font-semibold hover:bg-blue-900/50 transition-colors text-center text-sm"
                    >
                      Download Mark Scheme
                    </a>
                  )}
                </div>

                {/* PDF Previews */}
                <div className="space-y-6">
                  {worksheetUrl && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-green-300 font-semibold text-sm">Question Paper Preview</h4>
                        <button
                          onClick={() => setFullscreenPdf({ url: worksheetUrl, title: 'Question Paper' })}
                          className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded-lg text-xs font-medium transition-colors"
                        >
                          Fullscreen
                        </button>
                      </div>
                      <iframe
                        src={worksheetUrl}
                        className="w-full h-[60vh] border-2 border-green-500/50 rounded-lg bg-white"
                        title="Question Paper Preview"
                      />
                    </div>
                  )}
                  {markschemeUrl && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-blue-300 font-semibold text-sm">Mark Scheme Preview</h4>
                        <button
                          onClick={() => setFullscreenPdf({ url: markschemeUrl, title: 'Mark Scheme' })}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-lg text-xs font-medium transition-colors"
                        >
                          Fullscreen
                        </button>
                      </div>
                      <iframe
                        src={markschemeUrl}
                        className="w-full h-[60vh] border-2 border-blue-500/50 rounded-lg bg-white"
                        title="Mark Scheme Preview"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* PDF Progress Bar */}
            {pdfProgress && (
              <div className="mt-4 bg-gray-900 border border-gray-600 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-white">{pdfProgress.label}</span>
                  <span className="text-xs text-gray-400">Step {pdfProgress.step} of {pdfProgress.total}</span>
                </div>
                <div className="w-full h-2.5 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${Math.round((pdfProgress.step / pdfProgress.total) * 100)}%`,
                      background: pdfProgress.step === pdfProgress.total
                        ? 'linear-gradient(to right, #22c55e, #10b981)'
                        : 'linear-gradient(to right, #3b82f6, #6366f1)',
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* ═══ RIGHT COLUMN: Test Basket ═══ */}
          <div className="lg:sticky lg:top-40 lg:self-start">
            <TestBasket
              items={basketItems}
              onRemove={removeFromBasket}
              onMoveUp={moveUp}
              onMoveDown={moveDown}
              onClearAll={clearBasket}
              onGenerate={handleGenerate}
              generating={generating}
              testTitle={testTitle}
              onTitleChange={setTestTitle}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
