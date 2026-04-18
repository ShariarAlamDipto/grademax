'use client';

import { useState, useEffect, useRef } from 'react';

// Fullscreen modal component for PDF preview
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
        <iframe
          src={url}
          className="w-full h-full border-0 rounded-lg bg-white"
          title={title}
        />
      </div>
    </div>
  );
}

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

const CURRENT_YEAR = new Date().getFullYear();
const START_YEAR = 2011;
const YEARS = Array.from({ length: CURRENT_YEAR - START_YEAR + 1 }, (_, i) => CURRENT_YEAR - i);

interface Question {
  id: string;
  questionNumber: string;
  topics: string[];
  difficulty: string;
  qpPageUrl: string;
  msPageUrl: string | null;
  hasDiagram: boolean;
  year: number;
  season: string;
  paper: string;
}

interface WorksheetGeneratorProps {
  initialSubjects: Subject[];
  initialTopics: Topic[];
}

export default function WorksheetGenerator({ initialSubjects, initialTopics }: WorksheetGeneratorProps) {
  // Subject and topic states — pre-populated from server, no loading needed
  const [subjects] = useState<Subject[]>(initialSubjects);
  const [topics, setTopics] = useState<Topic[]>(initialTopics);
  const [loadingTopics, setLoadingTopics] = useState(false);
  
  const [selectedSubject, setSelectedSubject] = useState<string>(initialSubjects[0]?.id || '');
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [yearStart, setYearStart] = useState<number>(START_YEAR);
  const [yearEnd, setYearEnd] = useState<number>(CURRENT_YEAR);
  const [difficulty, setDifficulty] = useState<string>('');
  const [limit, setLimit] = useState<number>(20);
  const [shuffle, setShuffle] = useState<boolean>(false);
  
  const [loading, setLoading] = useState(false);
  const [pdfProgress, setPdfProgress] = useState<{ step: number; total: number; label: string } | null>(null);
  const [worksheetId, setWorksheetId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const [worksheetUrl, setWorksheetUrl] = useState<string | null>(null);
  const [markschemeUrl, setMarkschemeUrl] = useState<string | null>(null);
  const [fullscreenPdf, setFullscreenPdf] = useState<{ url: string; title: string } | null>(null);

  // Cache topics per subject to avoid re-fetching
  const topicsCache = useRef<Record<string, Topic[]>>({
    [initialSubjects[0]?.id || '']: initialTopics,
  });

  // Fetch topics only when subject changes (with cache)
  useEffect(() => {
    if (!selectedSubject) return;
    
    // Return cached topics if available
    if (topicsCache.current[selectedSubject]) {
      setTopics(topicsCache.current[selectedSubject]);
      return;
    }

    async function fetchTopics() {
      setLoadingTopics(true);
      try {
        const response = await fetch(`/api/topics?subjectId=${selectedSubject}`);
        const data = await response.json();
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

  // Reset selected topics when subject changes — revoke any live object URLs
  useEffect(() => {
    setSelectedTopics([]);
    setQuestions([]);
    setWorksheetId(null);
    setWorksheetUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setMarkschemeUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setError(null);
  }, [selectedSubject]);

  const toggleTopic = (code: string) => {
    setSelectedTopics(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  const handleGenerate = async () => {
    if (selectedTopics.length === 0) {
      setError('Please select at least one topic');
      return;
    }
    if (yearStart > yearEnd) {
      setError('Start year cannot be after end year');
      return;
    }

    setLoading(true);
    setError(null);
    setWorksheetId(null);
    setQuestions([]);

    // Revoke any existing object URLs before creating new ones
    setWorksheetUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setMarkschemeUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });

    try {
      const response = await fetch('/api/worksheets/generate-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subjectId: selectedSubject,
          topics: selectedTopics,
          yearStart,
          yearEnd,
          difficulty: difficulty || undefined,
          limit,
          shuffle
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate worksheet');
      }

      if (!data.pages || data.pages.length === 0) {
        setError('No questions found matching your criteria. Try different filters.');
        return;
      }

      setWorksheetId(data.worksheet_id);
      setQuestions(data.pages);

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate worksheet');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!worksheetId) return;

    setError(null);
    // Revoke any previously created object URLs
    setWorksheetUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setMarkschemeUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });

    try {
      // Step 1: Download worksheet PDF
      setPdfProgress({ step: 1, total: 3, label: 'Building worksheet PDF...' });
      const worksheetResponse = await fetch(`/api/worksheets/${worksheetId}/download?type=worksheet`);
      
      if (!worksheetResponse.ok) {
        const error = await worksheetResponse.json();
        throw new Error(error.error || 'Failed to generate worksheet PDF');
      }

      const worksheetBlob = await worksheetResponse.blob();
      const wUrl = URL.createObjectURL(worksheetBlob);
      setWorksheetUrl(wUrl);

      // Step 2: Download markscheme PDF
      setPdfProgress({ step: 2, total: 3, label: 'Building markscheme PDF...' });
      const markschemeResponse = await fetch(`/api/worksheets/${worksheetId}/download?type=markscheme`);
      
      if (markschemeResponse.ok) {
        const markschemeBlob = await markschemeResponse.blob();
        const msUrl = URL.createObjectURL(markschemeBlob);
        setMarkschemeUrl(msUrl);
      }

      // Step 3: Done
      setPdfProgress({ step: 3, total: 3, label: 'PDFs ready!' });
      setTimeout(() => setPdfProgress(null), 2000);

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate PDFs');
      setPdfProgress(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 p-4 md:p-8">
      {/* Fullscreen PDF Modal */}
      {fullscreenPdf && (
        <FullscreenPdfModal
          url={fullscreenPdf.url}
          title={fullscreenPdf.title}
          onClose={() => setFullscreenPdf(null)}
        />
      )}
      
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl md:text-5xl font-bold mb-2 text-white">Worksheet Generator</h1>
        <p className="text-gray-300 mb-4 md:mb-8 text-sm md:text-base">
          Select subject, topics, year range, and difficulty to create custom worksheets
        </p>

        {/* Filters Panel */}
        <div className="bg-gray-800 bg-opacity-80 backdrop-blur-lg rounded-xl md:rounded-2xl shadow-xl p-4 md:p-8 mb-4 md:mb-8 border border-gray-700">
          
          {/* Subject Selection */}
          <div className="mb-4 md:mb-8">
            <h2 className="text-lg md:text-2xl font-semibold mb-3 md:mb-4 flex items-center gap-2 text-white">
              Select Subject
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-5 gap-2 md:gap-4">
              {subjects.length === 0 ? (
                <div className="col-span-full text-center py-4 md:py-8 text-gray-400">
                  <p className="text-base md:text-lg mb-2">No subjects available</p>
                  <p className="text-xs md:text-sm">Please contact the administrator</p>
                </div>
              ) : (
                subjects.map((subject) => (
                  <button
                    key={subject.id}
                    onClick={() => setSelectedSubject(subject.id)}
                    className={`p-2 md:p-4 rounded-lg md:rounded-xl border-2 transition-all ${
                      selectedSubject === subject.id
                        ? 'border-amber-500 bg-amber-900 bg-opacity-50 shadow-lg'
                        : 'border-gray-600 bg-gray-700 bg-opacity-50 hover:border-gray-500'
                    }`}
                  >
                    <div className="text-[10px] md:text-xs text-gray-400 font-medium mb-0.5 md:mb-1">{subject.code}</div>
                    <div className="text-[10px] md:text-xs text-gray-400 font-medium">{subject.level || 'IGCSE'}</div>
                    <div className="text-xs md:text-sm font-semibold text-white text-center">{subject.name}</div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Topic Selection */}
          <div className="mb-4 md:mb-8">
            <h2 className="text-lg md:text-2xl font-semibold mb-3 md:mb-4 flex flex-wrap items-center gap-2 text-white">
              Select Topics
              {selectedTopics.length > 0 && (
                <span className="text-xs md:text-sm bg-blue-500 text-white px-2 md:px-3 py-0.5 md:py-1 rounded-full">
                  {selectedTopics.length} selected
                </span>
              )}
            </h2>
            
            {loadingTopics ? (
              <div className="flex items-center justify-center p-4 md:p-8">
                <div className="animate-spin rounded-full h-6 w-6 md:h-8 md:w-8 border-b-2 border-white"></div>
              </div>
            ) : topics.length === 0 ? (
              <div className="text-center p-4 md:p-8 bg-gray-700 bg-opacity-30 rounded-xl">
                <p className="text-gray-400 text-sm md:text-base">No topics available for this subject yet</p>
              </div>
            ) : (
              <div className="overflow-x-auto -mx-4 md:mx-0">
                <table className="w-full border-collapse min-w-[300px]">
                  <thead>
                    <tr className="bg-gray-700 bg-opacity-50">
                      <th className="border border-gray-600 px-2 md:px-4 py-2 md:py-3 text-left text-white font-semibold text-xs md:text-base">Select</th>
                      <th className="border border-gray-600 px-2 md:px-4 py-2 md:py-3 text-left text-white font-semibold text-xs md:text-base">Code</th>
                      <th className="border border-gray-600 px-2 md:px-4 py-2 md:py-3 text-left text-white font-semibold text-xs md:text-base">Topic Name</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topics.map((topic) => (
                      <tr 
                        key={topic.id}
                        onClick={() => toggleTopic(topic.code)}
                        className={`transition-colors cursor-pointer ${
                          selectedTopics.includes(topic.code)
                            ? 'bg-blue-900 bg-opacity-50 border-blue-500'
                            : 'bg-gray-700 bg-opacity-30 hover:bg-gray-600 hover:bg-opacity-40'
                        }`}
                      >
                        <td className="border border-gray-600 px-2 md:px-4 py-2 md:py-3 text-center">
                          <div 
                            className="relative flex items-center justify-center w-10 h-10 md:w-12 md:h-12 cursor-pointer mx-auto"
                            onClick={(e) => { e.stopPropagation(); toggleTopic(topic.code); }}
                          >
                            <div className={`w-7 h-7 md:w-8 md:h-8 rounded-lg border-2 transition-all flex items-center justify-center ${
                              selectedTopics.includes(topic.code) 
                                ? 'bg-blue-600 border-blue-400' 
                                : 'bg-gray-600 border-gray-500 hover:border-gray-400'
                            }`}>
                              {selectedTopics.includes(topic.code) && (
                                <svg className="w-5 h-5 md:w-6 md:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="border border-gray-600 px-2 md:px-4 py-2 md:py-3">
                          <span className="text-white font-semibold text-xs md:text-base">{topic.code}</span>
                        </td>
                        <td className="border border-gray-600 px-2 md:px-4 py-2 md:py-3">
                          <span className="text-white text-xs md:text-base">{topic.name}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Year Range */}
          <div className="grid grid-cols-2 gap-3 md:gap-6 mb-4 md:mb-8">
            <div>
              <label className="block text-xs md:text-sm font-semibold text-gray-300 mb-1 md:mb-2">
                Start Year
              </label>
              <select
                value={yearStart}
                onChange={(e) => setYearStart(parseInt(e.target.value))}
                className="w-full p-2 md:p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none text-sm md:text-base"
              >
                {YEARS.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs md:text-sm font-semibold text-gray-300 mb-1 md:mb-2">
                End Year
              </label>
              <select
                value={yearEnd}
                onChange={(e) => setYearEnd(parseInt(e.target.value))}
                className="w-full p-2 md:p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none text-sm md:text-base"
              >
                {YEARS.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Additional Filters */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-6 mb-4 md:mb-8">
            <div>
              <label className="block text-xs md:text-sm font-semibold text-gray-300 mb-1 md:mb-2">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full p-2 md:p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none text-sm md:text-base"
              >
                <option value="">All</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <div>
              <label className="block text-xs md:text-sm font-semibold text-gray-300 mb-1 md:mb-2">
                Max Questions
              </label>
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value) || 20)}
                min="1"
                max="100"
                className="w-full p-2 md:p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none text-sm md:text-base"
              />
            </div>
            <div className="col-span-2 md:col-span-1 flex items-end">
              <label className="flex items-center gap-2 cursor-pointer p-2 md:p-3 border-2 border-gray-600 bg-gray-700 rounded-lg hover:border-blue-500 w-full">
                <input
                  type="checkbox"
                  checked={shuffle}
                  onChange={(e) => setShuffle(e.target.checked)}
                  className="w-4 h-4 md:w-5 md:h-5"
                />
                <span className="text-xs md:text-sm font-semibold text-white">Shuffle Questions</span>
              </label>
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={loading || selectedTopics.length === 0}
            className="w-full bg-gradient-to-r from-amber-500 to-yellow-400 text-gray-900 py-3 md:py-4 rounded-xl font-bold text-base md:text-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Generating...' : 'Generate Worksheet'}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900 bg-opacity-80 backdrop-blur-lg border-2 border-red-500 rounded-xl p-4 md:p-6 mb-4 md:mb-8">
            <div className="flex items-center gap-3">
              <div>
                <div className="font-bold text-red-300 text-sm md:text-base">Error</div>
                <div className="text-red-200 text-sm md:text-base">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {questions.length > 0 && (
          <div className="bg-gray-800 bg-opacity-80 backdrop-blur-lg rounded-xl md:rounded-2xl shadow-xl p-4 md:p-8 border border-gray-700">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4 md:mb-6">
              <div>
                <h2 className="text-lg md:text-2xl font-bold text-white">
                  Generated Worksheet
                </h2>
                <p className="text-gray-300 text-xs md:text-base">
                  {questions.length} questions • {selectedTopics.join(', ')}
                </p>
              </div>
              
              <button
                onClick={handleDownload}
                disabled={pdfProgress !== null}
                className="w-full sm:w-auto bg-green-500 text-white px-4 md:px-6 py-2 md:py-3 rounded-lg font-semibold hover:bg-green-600 transition-colors disabled:opacity-50 text-sm md:text-base"
              >
                {pdfProgress ? pdfProgress.label : 'Download PDFs'}
              </button>
            </div>

            {/* PDF Progress Bar */}
            {pdfProgress && (
              <div className="bg-gray-900 border border-gray-600 rounded-xl p-4 md:p-6 mb-4 md:mb-6">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-white">{pdfProgress.label}</span>
                  <span className="text-xs text-gray-400">Step {pdfProgress.step} of {pdfProgress.total}</span>
                </div>
                <div className="w-full h-3 bg-gray-700 rounded-full overflow-hidden">
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
                <div className="flex justify-between mt-3 gap-1">
                  {['Worksheet PDF', 'Markscheme PDF', 'Complete'].map((stepLabel, i) => (
                    <div key={stepLabel} className="flex items-center gap-1.5 text-xs">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        i + 1 < pdfProgress.step
                          ? 'bg-green-400'
                          : i + 1 === pdfProgress.step
                          ? 'bg-blue-400 animate-pulse'
                          : 'bg-gray-600'
                      }`} />
                      <span className={
                        i + 1 < pdfProgress.step
                          ? 'text-green-400'
                          : i + 1 === pdfProgress.step
                          ? 'text-blue-300'
                          : 'text-gray-500'
                      }>{stepLabel}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Download Links */}
            {(worksheetUrl || markschemeUrl) && (
              <div className="bg-gradient-to-r from-green-900 to-emerald-900 bg-opacity-50 border-2 border-green-500 rounded-xl p-4 md:p-6 mb-4 md:mb-6">
                <h3 className="font-bold text-green-300 mb-3 md:mb-4 text-base md:text-lg">PDFs Ready!</h3>
                <div className="flex flex-col sm:flex-row gap-3 md:gap-4 mb-4 md:mb-6">
                  {worksheetUrl && (
                    <a
                      href={worksheetUrl}
                      download="worksheet.pdf"
                      className="flex-1 bg-gray-700 border-2 border-green-500 text-green-300 px-4 md:px-6 py-2 md:py-3 rounded-lg font-semibold hover:bg-green-900 transition-colors text-center text-sm md:text-base"
                    >
                      Download Worksheet.pdf
                    </a>
                  )}
                  {markschemeUrl && (
                    <a
                      href={markschemeUrl}
                      download="markscheme.pdf"
                      className="flex-1 bg-gray-700 border-2 border-blue-500 text-blue-300 px-4 md:px-6 py-2 md:py-3 rounded-lg font-semibold hover:bg-blue-900 transition-colors text-center text-sm md:text-base"
                    >
                      Download Markscheme.pdf
                    </a>
                  )}
                </div>

                {/* PDF Previews */}
                <div className="flex flex-col items-center gap-6 md:gap-8">
                  {worksheetUrl && (
                    <div className="w-full flex flex-col items-center">
                      <div className="flex items-center justify-between w-full mb-3 md:mb-4">
                        <h4 className="text-green-300 font-semibold text-base md:text-xl">Worksheet Preview</h4>
                        <button
                          onClick={() => setFullscreenPdf({ url: worksheetUrl, title: 'Worksheet Preview' })}
                          className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 md:px-4 md:py-2 rounded-lg font-semibold text-xs md:text-sm transition-colors"
                        >
                          Fullscreen
                        </button>
                      </div>
                      <iframe 
                        src={worksheetUrl} 
                        className="w-full md:w-[85vw] lg:w-[80vw] h-[50vh] md:h-[70vh] lg:h-[85vh] border-2 border-green-500 rounded-lg bg-white shadow-2xl"
                        title="Worksheet Preview"
                      />
                    </div>
                  )}
                  {markschemeUrl && (
                    <div className="w-full flex flex-col items-center mt-4 md:mt-8">
                      <div className="flex items-center justify-between w-full mb-3 md:mb-4">
                        <h4 className="text-blue-300 font-semibold text-base md:text-xl">Markscheme Preview</h4>
                        <button
                          onClick={() => setFullscreenPdf({ url: markschemeUrl, title: 'Markscheme Preview' })}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 md:px-4 md:py-2 rounded-lg font-semibold text-xs md:text-sm transition-colors"
                        >
                          Fullscreen
                        </button>
                      </div>
                      <iframe 
                        src={markschemeUrl} 
                        className="w-full md:w-[85vw] lg:w-[80vw] h-[50vh] md:h-[70vh] lg:h-[85vh] border-2 border-blue-500 rounded-lg bg-white shadow-2xl"
                        title="Markscheme Preview"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Question List */}
            <div className="space-y-2 md:space-y-3">
              {questions.map((q, index) => (
                <div
                  key={q.id}
                  className="border-2 border-gray-600 bg-gray-700 bg-opacity-50 rounded-lg p-3 md:p-4 hover:border-blue-500 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-3 md:gap-4">
                      <div className="bg-blue-500 text-white w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center font-bold text-sm md:text-base flex-shrink-0">
                        {index + 1}
                      </div>
                      <div>
                        <div className="font-semibold text-white text-sm md:text-base">
                          Question {q.questionNumber}
                        </div>
                        <div className="text-xs md:text-sm text-gray-300">
                          {q.year} {q.season} • Paper {q.paper}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5 md:gap-2 ml-11 sm:ml-0">
                      {q.topics.map((topic: string) => (
                        <span
                          key={topic}
                          className="px-2 md:px-3 py-0.5 md:py-1 bg-blue-900 text-blue-300 border border-blue-500 rounded-full text-xs md:text-sm font-medium"
                        >
                          {topic}
                        </span>
                      ))}
                      {q.difficulty && (
                        <span className={`px-2 md:px-3 py-0.5 md:py-1 rounded-full text-xs md:text-sm font-medium border ${
                          q.difficulty === 'easy' ? 'bg-green-900 text-green-300 border-green-500' :
                          q.difficulty === 'medium' ? 'bg-yellow-900 text-yellow-300 border-yellow-500' :
                          'bg-red-900 text-red-300 border-red-500'
                        }`}>
                          {q.difficulty}
                        </span>
                      )}
                      {q.hasDiagram && (
                        <span className="px-2 md:px-3 py-0.5 md:py-1 bg-amber-900 text-amber-300 border border-amber-500 rounded-full text-xs md:text-sm">
                          Diagram
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
