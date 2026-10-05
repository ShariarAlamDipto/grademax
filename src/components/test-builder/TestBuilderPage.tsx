'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { limitMessage } from '@/lib/toolLimits';
import { useQuestionLimit } from '@/lib/useQuestionLimit';

function fireTrack(feature: string, payload?: Record<string, unknown>) {
  fetch("/api/track", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feature, ...payload }),
  }).catch(() => undefined);
}

import SubjectSelector from './SubjectSelector';
import TopicTree from './TopicTree';
import FilterBar from './FilterBar';
import QuestionCard, { QuestionItem } from './QuestionCard';
import PaperPreview from './PaperPreview';
import QuestionPreviewModal from './QuestionPreviewModal';
import { buildPdfInBrowser } from '@/lib/clientPdfBuild';
import { pageWindow } from '@/lib/pagination';
import {
  BASKET_STORAGE_KEY,
  parseStoredBasket,
  serializeBasket,
  type StoredBasket,
} from '@/lib/basketStorage';

/** Tailwind `lg` — below this the inline preview column is hidden. */
const LG_BREAKPOINT_PX = 1024;
/** Desktop navbar height (68px + 1px border); replaced by a measurement once the drawer opens. */
const DEFAULT_NAV_HEIGHT_PX = 69;
/** Shown when questions are added/removed while a PDF is still building. */
const STALE_BASKET_MESSAGE = 'Your questions changed while the PDF was building. Tap Generate again.';
/** Page-number buttons: wider screens vs phones (see the pagination nav). */
const PAGE_BUTTONS_WIDE = 7;
const PAGE_BUTTONS_PHONE = 3;
/** How long a basket notice toast stays up. */
const NOTICE_MS = 4000;

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
  const { limit: questionLimit } = useQuestionLimit();

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
  // The blobs are kept alongside their object URLs because iOS saves via the
  // Web Share API, which needs the bytes as a File — and it must be handed
  // them synchronously inside the click, so re-fetching the URL is too late.
  const [worksheetBlob, setWorksheetBlob] = useState<Blob | null>(null);
  const [markschemeBlob, setMarkschemeBlob] = useState<Blob | null>(null);
  const [pdfProgress, setPdfProgress] = useState<{ step: number; total: number; label: string } | null>(null);
  // Three separate channels so each message shows where the student is
  // looking: search errors above the results, PDF errors in the preview
  // footer, and basket notices as a toast (the results header is usually
  // scrolled far out of view when "+ Add" is tapped on a phone).
  const [error, setError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // ── Basket helpers ──
  const basketIds = useMemo(() => new Set(basketItems.map(i => i.id)), [basketItems]);
  // Bumped on every basket change, so a PDF build can tell if the basket
  // moved under it and discard a result that no longer matches.
  const basketVersion = useRef(0);
  const pendingRestore = useRef<StoredBasket | null>(null);
  const [basketHydrated, setBasketHydrated] = useState(false);
  const resultsTopRef = useRef<HTMLDivElement>(null);

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

  // Reset when subject changes — clear basket and any previously generated PDFs.
  // Skipped on mount: there is nothing to reset yet, and running it would
  // wipe a basket the restore effect below has just put back.
  const lastSubject = useRef<string | null>(null);
  useEffect(() => {
    const changed = lastSubject.current !== null && lastSubject.current !== selectedSubject;
    lastSubject.current = selectedSubject;
    if (changed) resetForSubject();

    if (selectedSubject) {
      const subject = initialSubjects.find(s => s.id === selectedSubject);
      fireTrack("test_builder_session", {
        subject_id: selectedSubject,
        subject_name: subject?.name ?? null,
      });
    }
  }, [selectedSubject]); // eslint-disable-line react-hooks/exhaustive-deps

  function resetForSubject() {
    setSelectedTopics([]);
    setQuestions([]);
    setPagination({ page: 1, limit: 20, total: 0, totalPages: 0 });
    setSearchTriggered(false);
    setError(null);
    setGenerateError(null);
    discardGeneratedPdfs();

    // A basket saved before the page was unloaded is restored once its
    // subject is selected; any other subject change starts a fresh basket.
    const restore = pendingRestore.current;
    if (restore && restore.subjectId === selectedSubject) {
      pendingRestore.current = null;
      setBasketItems(restore.items);
      setTestTitle(restore.title);
    } else {
      setBasketItems([]);
    }
  }

  // "Mobile" must match the `lg` breakpoint that hides the inline preview
  // column, or 768-1023px screens get no preview at all. The drawer is
  // never auto-opened: students keep adding questions and open it from the
  // bottom bar when they are ready to build the PDF.
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < LG_BREAKPOINT_PX);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Restore a basket saved this session (e.g. before iOS navigated away to
  // a generated PDF). Same subject → apply now; otherwise switch subject and
  // let the reset effect above apply it.
  useEffect(() => {
    let saved: StoredBasket | null = null;
    try {
      saved = parseStoredBasket(window.sessionStorage.getItem(BASKET_STORAGE_KEY));
    } catch {
      // Storage blocked (private mode) — nothing to restore.
    }
    setBasketHydrated(true);
    if (!saved || saved.items.length === 0) return;
    if (!initialSubjects.some(s => s.id === saved.subjectId)) return;

    if (saved.subjectId === selectedSubject) {
      setBasketItems(saved.items);
      setTestTitle(saved.title);
    } else {
      pendingRestore.current = saved;
      setSelectedSubject(saved.subjectId);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Don't overwrite a saved basket before it has been read back, or while
    // it is still waiting for its subject to be selected.
    if (!basketHydrated || pendingRestore.current) return;
    try {
      if (basketItems.length === 0) {
        window.sessionStorage.removeItem(BASKET_STORAGE_KEY);
      } else {
        window.sessionStorage.setItem(
          BASKET_STORAGE_KEY,
          serializeBasket({ subjectId: selectedSubject, title: testTitle, items: basketItems }),
        );
      }
    } catch {
      // Storage full or blocked — the basket still works, it just won't survive a reload.
    }
  }, [basketItems, testTitle, selectedSubject, basketHydrated]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  // Lock the page behind the mobile drawer so scrolling the preview doesn't
  // scroll the question list underneath it (iOS scroll chaining).
  const drawerOpen = isMobile && showMobilePreview;
  useEffect(() => {
    if (!drawerOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [drawerOpen]);

  // The drawer must start below the fixed navbar, whose height varies by
  // breakpoint (two rows, ~117px, on phones). A hard-coded offset hid the
  // drawer's header — and its only close button — behind the nav pills.
  const [navBottom, setNavBottom] = useState(DEFAULT_NAV_HEIGHT_PX);
  useEffect(() => {
    if (!drawerOpen) return;
    const measure = () => {
      const nav = document.querySelector('nav[aria-label="Main navigation"]');
      if (nav) setNavBottom(Math.max(0, Math.round(nav.getBoundingClientRect().bottom)));
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [drawerOpen]);

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

  // After a page change, bring the student back to the top of the results —
  // on a phone the page buttons sit far below the first new question.
  // Scrolls once the new page has rendered — scrolling while the list is
  // being swapped out gets cancelled by the layout shift in WebKit.
  const scrollAfterLoad = useRef(false);
  const goToPage = (page: number) => {
    scrollAfterLoad.current = true;
    void fetchQuestions(page);
  };
  useEffect(() => {
    if (loadingQuestions || !scrollAfterLoad.current) return;
    scrollAfterLoad.current = false;
    resultsTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [loadingQuestions]);
  const mobileWindow = pageWindow(pagination.page, pagination.totalPages, PAGE_BUTTONS_PHONE);

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

  /** Drop any generated PDFs (revoking their object URLs). */
  function discardGeneratedPdfs() {
    setWorksheetUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setMarkschemeUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setWorksheetBlob(null);
    setMarkschemeBlob(null);
  }

  /**
   * Every basket edit goes through here: a PDF built from the old basket no
   * longer matches, so its download links are withdrawn rather than letting
   * the student download a stale paper.
   */
  const updateBasket = (next: (prev: QuestionItem[]) => QuestionItem[]) => {
    basketVersion.current += 1;
    setBasketItems(next);
    setGenerateError(null);
    discardGeneratedPdfs();
  };

  const addToBasket = (q: QuestionItem) => {
    if (basketIds.has(q.id)) return;
    if (questionLimit !== null && basketItems.length >= questionLimit) {
      setNotice(limitMessage(questionLimit));
      return;
    }
    updateBasket(prev => [...prev, q]);
  };

  const removeFromBasket = (id: string) => {
    updateBasket(prev => prev.filter(i => i.id !== id));
  };

  const swap = (items: QuestionItem[], a: number, b: number): QuestionItem[] =>
    items.map((item, i) => (i === a ? items[b] : i === b ? items[a] : item));

  const moveUp = (index: number) => {
    if (index <= 0) return;
    updateBasket(prev => swap(prev, index - 1, index));
  };

  const moveDown = (index: number) => {
    if (index >= basketItems.length - 1) return;
    updateBasket(prev => swap(prev, index, index + 1));
  };

  const clearBasket = () => {
    updateBasket(() => []);
  };

  // ─────────────────────────────────────────────
  // Generate test PDF
  // ─────────────────────────────────────────────

  const handleGenerate = async () => {
    if (basketItems.length === 0) return;

    setGenerating(true);
    setGenerateError(null);
    discardGeneratedPdfs();
    const startedAtVersion = basketVersion.current;
    const basketChanged = () => basketVersion.current !== startedAtVersion;

    const subject = initialSubjects.find(s => s.id === selectedSubject);
    const totalMarks = basketItems.length * 4;
    const pagesPayload = basketItems.map(item => ({
      qpPageUrl: item.qpPageUrl,
      msPageUrl: item.msPageUrl,
    }));

    try {
      // Step 1: Build question paper PDF entirely in the browser.
      // (See src/lib/clientPdfBuild.ts for why we no longer round-trip through
      // the server PDF-merge route — short version: phones over cellular kept
      // dropping the long single response, so the merge now happens locally
      // with parallel fetches from Supabase storage.)
      const qpResult = await buildPdfInBrowser(pagesPayload, {
        kind: 'worksheet',
        title: testTitle || 'Untitled Test',
        subjectName: subject?.name || '',
        level: subject?.level || '',
        totalMarks,
        brand: 'GradeMax Exams',
      }, (p) => {
        setPdfProgress({
          step: 1,
          total: 2,
          label: `Question paper · ${p.label}`,
        });
      });

      if (qpResult.successCount === 0) {
        throw new Error('No question PDFs could be downloaded. Please try again or check your connection.');
      }

      if (basketChanged()) throw new Error(STALE_BASKET_MESSAGE);
      setWorksheetBlob(qpResult.blob);
      setWorksheetUrl(URL.createObjectURL(qpResult.blob));

      // Step 2: Mark scheme is best-effort — failure here keeps the QP we
      // already produced and just warns.
      try {
        const hasAnyMs = pagesPayload.some((p) => p.msPageUrl);
        if (hasAnyMs) {
          const msResult = await buildPdfInBrowser(pagesPayload, {
            kind: 'markscheme',
            title: testTitle || 'Untitled Test',
            subjectName: subject?.name || '',
            level: subject?.level || '',
            totalMarks,
            brand: 'GradeMax Exams',
          }, (p) => {
            setPdfProgress({
              step: 2,
              total: 2,
              label: `Mark scheme · ${p.label}`,
            });
          });
          if (msResult.successCount > 0 && !basketChanged()) {
            setMarkschemeBlob(msResult.blob);
            setMarkschemeUrl(URL.createObjectURL(msResult.blob));
          }
        }
      } catch (msErr) {
        console.warn('[TestBuilder] mark scheme generation failed', msErr);
      }

      if (basketChanged()) throw new Error(STALE_BASKET_MESSAGE);

      // Step 3: Done
      setPdfProgress({ step: 2, total: 2, label: 'PDFs ready!' });
      setTimeout(() => setPdfProgress(null), 2000);

      fireTrack("test_builder_download", {
        subject_id: selectedSubject,
        subject_name: initialSubjects.find(s => s.id === selectedSubject)?.name ?? null,
        metadata: { question_count: basketItems.length, title: testTitle || 'Untitled Test' },
      });

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
      console.error('[TestBuilder] generate failed', err);
      setGenerateError(err instanceof Error ? err.message : 'Failed to generate PDF');
      setPdfProgress(null);
    } finally {
      setGenerating(false);
    }
  };

  // ─────────────────────────────────────────────
  // Render
  //
  // Note: download links are rendered inside <PaperPreview> as real <a> tags
  // so desktop and Android use the browser's native download path untouched.
  // iOS honours neither `download` nor `target="_blank"` on a blob: URL, so
  // the handlers in @/lib/savePdf intercept the click there and hand the PDF
  // to the native share sheet ("Save to Files") instead. Both blobs are held
  // in state because that share call must receive a File synchronously.
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

      <div className={`max-w-[1800px] mx-auto p-4 md:p-6 ${isMobile && basketItems.length > 0 ? 'pb-28' : ''}`}>
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
          {/* Always mounted (unlike the results header, which unmounts while
              loading) so a page change has something to scroll to. */}
          <div ref={resultsTopRef} className="min-w-0">
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
                  // Phones show 3 page numbers, wider screens 7, and the row
                  // wraps rather than overflowing: 7 numbers + Previous/Next
                  // is ~480px, wider than a phone, and the page clips
                  // horizontal overflow — which hid both Previous and Next.
                  <nav aria-label="Question pages" className="flex flex-wrap items-center justify-center gap-2">
                    <button
                      onClick={() => goToPage(pagination.page - 1)}
                      disabled={pagination.page <= 1}
                      className="px-3 sm:px-4 py-2 text-sm bg-gray-800 border border-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Previous
                    </button>
                    {pageWindow(pagination.page, pagination.totalPages, PAGE_BUTTONS_WIDE).map((pageNum) => {
                      const onPhone = mobileWindow.includes(pageNum);
                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          aria-current={pageNum === pagination.page ? 'page' : undefined}
                          className={`${onPhone ? 'inline-flex' : 'hidden sm:inline-flex'} items-center justify-center w-9 h-9 text-sm rounded-lg transition-colors ${
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
                      onClick={() => goToPage(pagination.page + 1)}
                      disabled={pagination.page >= pagination.totalPages}
                      className="px-3 sm:px-4 py-2 text-sm bg-gray-800 border border-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                    </button>
                  </nav>
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

          {/* ═══ RIGHT COLUMN: Live Paper Preview ═══
              Hidden on phones — the mobile drawer below renders its own
              instance. Without `hidden lg:block` the inline column
              duplicates the drawer content under the question grid. */}
          <div className="hidden lg:block lg:sticky lg:top-24 lg:self-start lg:h-[calc(100vh-7rem)] lg:max-h-[calc(100vh-7rem)]">
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
              worksheetBlob={worksheetBlob}
              markschemeBlob={markschemeBlob}
              pdfProgress={pdfProgress}
              error={generateError}
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

            {/* Drawer Panel — starts below the fixed navbar (measured above). */}
            <div style={{ top: navBottom }} className="fixed bottom-0 left-0 right-0 z-40 bg-gradient-to-br from-gray-900 via-black to-gray-900 flex flex-col rounded-t-2xl overflow-hidden">
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
                  worksheetBlob={worksheetBlob}
                  markschemeBlob={markschemeBlob}
                  pdfProgress={pdfProgress}
                  error={generateError}
                />
              </div>
            </div>
          </>
        )}

        {/* Basket notice toast (e.g. question limit reached). Sits above the
            mobile bottom bar and above the question preview modal, since
            "+ Add to Test" can be tapped from either. */}
        {notice && (
          <div
            role="status"
            className={`fixed left-4 right-4 z-[70] mx-auto max-w-md rounded-xl border border-amber-500/60 bg-gray-900/95 px-4 py-3 text-sm text-amber-200 shadow-2xl backdrop-blur ${
              isMobile && basketItems.length > 0 && !showMobilePreview ? 'bottom-24' : 'bottom-6'
            }`}
          >
            {notice}
          </div>
        )}

        {/* Mobile bottom bar: keeps the question list usable while the
            basket fills, and opens the preview / PDF step on demand. */}
        {isMobile && basketItems.length > 0 && !showMobilePreview && (
          <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-gray-700 bg-gray-900/95 backdrop-blur px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
            <div className="flex items-center gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white">
                  {basketItems.length} question{basketItems.length === 1 ? '' : 's'} added
                </p>
                <p className="text-xs text-gray-400 truncate">Keep adding, then build your PDF</p>
              </div>
              <button
                onClick={() => setShowMobilePreview(true)}
                className="shrink-0 px-5 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-sm font-semibold rounded-lg shadow-lg active:scale-95 transition-transform"
              >
                Build PDF
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
