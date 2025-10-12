'use client';

import { useState } from 'react';

const TOPICS = [
  { code: '1', name: 'Forces and motion', icon: '🚗' },
  { code: '2', name: 'Electricity', icon: '⚡' },
  { code: '3', name: 'Waves', icon: '🌊' },
  { code: '4', name: 'Energy resources', icon: '🔋' },
  { code: '5', name: 'Solids, liquids and gases', icon: '💧' },
  { code: '6', name: 'Magnetism and electromagnetism', icon: '🧲' },
  { code: '7', name: 'Radioactivity and particles', icon: '☢️' },
  { code: '8', name: 'Astrophysics', icon: '🌌' },
];

const CURRENT_YEAR = 2025;
const YEARS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR - i);

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

export default function WorksheetGeneratorPage() {
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [yearStart, setYearStart] = useState<number>(2017);
  const [yearEnd, setYearEnd] = useState<number>(CURRENT_YEAR);
  const [difficulty, setDifficulty] = useState<string>('');
  const [limit, setLimit] = useState<number>(20);
  const [shuffle, setShuffle] = useState<boolean>(false);
  
  const [loading, setLoading] = useState(false);
  const [generatingPDF, setGeneratingPDF] = useState(false);
  const [worksheetId, setWorksheetId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const [worksheetUrl, setWorksheetUrl] = useState<string | null>(null);
  const [markschemeUrl, setMarkschemeUrl] = useState<string | null>(null);

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

    setLoading(true);
    setError(null);
    setWorksheetId(null);
    setQuestions([]);
    setWorksheetUrl(null);
    setMarkschemeUrl(null);

    try {
      const response = await fetch('/api/worksheets/generate-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subjectCode: '4PH1',
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

      if (data.pages.length === 0) {
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

    setGeneratingPDF(true);
    setError(null);

    try {
      // Download worksheet PDF
      const worksheetResponse = await fetch(`/api/worksheets/${worksheetId}/download?type=worksheet`);
      
      if (!worksheetResponse.ok) {
        const error = await worksheetResponse.json();
        throw new Error(error.error || 'Failed to generate worksheet PDF');
      }

      const worksheetBlob = await worksheetResponse.blob();
      const worksheetUrl = URL.createObjectURL(worksheetBlob);
      setWorksheetUrl(worksheetUrl);

      // Download markscheme PDF
      const markschemeResponse = await fetch(`/api/worksheets/${worksheetId}/download?type=markscheme`);
      
      if (markschemeResponse.ok) {
        const markschemeBlob = await markschemeResponse.blob();
        const markschemeUrl = URL.createObjectURL(markschemeBlob);
        setMarkschemeUrl(markschemeUrl);
      }

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate PDFs');
    } finally {
      setGeneratingPDF(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-5xl font-bold mb-2 text-white">📝 Worksheet Generator</h1>
        <p className="text-gray-300 mb-8">
          Select topics, year range, and difficulty to create custom worksheets with mark schemes
        </p>

        {/* Filters Panel */}
        <div className="bg-gray-800 bg-opacity-80 backdrop-blur-lg rounded-2xl shadow-xl p-8 mb-8 border border-gray-700">
          {/* Topic Selection */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2 text-white">
              🎯 Select Topics
              {selectedTopics.length > 0 && (
                <span className="text-sm bg-blue-500 text-white px-3 py-1 rounded-full">
                  {selectedTopics.length} selected
                </span>
              )}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {TOPICS.map((topic) => (
                <button
                  key={topic.code}
                  onClick={() => toggleTopic(topic.code)}
                  className={`p-4 rounded-xl border-2 transition-all transform hover:scale-105 ${
                    selectedTopics.includes(topic.code)
                      ? 'border-blue-500 bg-blue-900 bg-opacity-50 shadow-lg shadow-blue-500/50'
                      : 'border-gray-600 bg-gray-700 bg-opacity-50 hover:border-gray-500 hover:shadow'
                  }`}
                >
                  <div className="text-3xl mb-2">{topic.icon}</div>
                  <div className="text-xs text-gray-400 font-medium">Topic {topic.code}</div>
                  <div className="text-sm font-semibold text-white">{topic.name}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Year Range */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">
                📅 Start Year
              </label>
              <select
                value={yearStart}
                onChange={(e) => setYearStart(parseInt(e.target.value))}
                className="w-full p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none"
              >
                {YEARS.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">
                📅 End Year
              </label>
              <select
                value={yearEnd}
                onChange={(e) => setYearEnd(parseInt(e.target.value))}
                className="w-full p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none"
              >
                {YEARS.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Additional Filters */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">
                💪 Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none"
              >
                <option value="">All Difficulties</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">
                📊 Max Questions
              </label>
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value) || 20)}
                min="1"
                max="100"
                className="w-full p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer p-3 border-2 border-gray-600 bg-gray-700 rounded-lg hover:border-blue-500 w-full">
                <input
                  type="checkbox"
                  checked={shuffle}
                  onChange={(e) => setShuffle(e.target.checked)}
                  className="w-5 h-5"
                />
                <span className="text-sm font-semibold text-white">🔀 Shuffle Questions</span>
              </label>
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={loading || selectedTopics.length === 0}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-4 rounded-xl font-bold text-lg shadow-lg hover:shadow-xl transform hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {loading ? '🔄 Generating...' : '✨ Generate Worksheet'}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900 bg-opacity-80 backdrop-blur-lg border-2 border-red-500 rounded-xl p-6 mb-8">
            <div className="flex items-center gap-3">
              <span className="text-3xl">❌</span>
              <div>
                <div className="font-bold text-red-300">Error</div>
                <div className="text-red-200">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {questions.length > 0 && (
          <div className="bg-gray-800 bg-opacity-80 backdrop-blur-lg rounded-2xl shadow-xl p-8 border border-gray-700">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  📋 Generated Worksheet
                </h2>
                <p className="text-gray-300">
                  {questions.length} questions found • Topics: {selectedTopics.join(', ')}
                </p>
              </div>
              
              <button
                onClick={handleDownload}
                disabled={generatingPDF}
                className="bg-green-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-600 transition-colors disabled:opacity-50"
              >
                {generatingPDF ? '📄 Creating PDFs...' : '⬇️ Download PDFs'}
              </button>
            </div>

            {/* Download Links */}
            {(worksheetUrl || markschemeUrl) && (
              <div className="bg-gradient-to-r from-green-900 to-emerald-900 bg-opacity-50 border-2 border-green-500 rounded-xl p-6 mb-6">
                <h3 className="font-bold text-green-300 mb-4 text-lg">✅ PDFs Ready!</h3>
                <div className="flex flex-wrap gap-4 mb-6">
                  {worksheetUrl && (
                    <a
                      href={worksheetUrl}
                      download="worksheet.pdf"
                      className="flex-1 bg-gray-700 border-2 border-green-500 text-green-300 px-6 py-3 rounded-lg font-semibold hover:bg-green-900 transition-colors text-center"
                    >
                      📝 Download Worksheet.pdf
                    </a>
                  )}
                  {markschemeUrl && (
                    <a
                      href={markschemeUrl}
                      download="markscheme.pdf"
                      className="flex-1 bg-gray-700 border-2 border-blue-500 text-blue-300 px-6 py-3 rounded-lg font-semibold hover:bg-blue-900 transition-colors text-center"
                    >
                      ✅ Download Markscheme.pdf
                    </a>
                  )}
                </div>

                {/* PDF Previews */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {worksheetUrl && (
                    <div>
                      <h4 className="text-green-300 font-semibold mb-2">📄 Worksheet Preview</h4>
                      <iframe 
                        src={worksheetUrl} 
                        className="w-full h-96 border-2 border-green-500 rounded-lg bg-white"
                        title="Worksheet Preview"
                      />
                    </div>
                  )}
                  {markschemeUrl && (
                    <div>
                      <h4 className="text-blue-300 font-semibold mb-2">✅ Markscheme Preview</h4>
                      <iframe 
                        src={markschemeUrl} 
                        className="w-full h-96 border-2 border-blue-500 rounded-lg bg-white"
                        title="Markscheme Preview"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Question List */}
            <div className="space-y-3">
              {questions.map((q, index) => (
                <div
                  key={q.id}
                  className="border-2 border-gray-600 bg-gray-700 bg-opacity-50 rounded-lg p-4 hover:border-blue-500 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="bg-blue-500 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold">
                        {index + 1}
                      </div>
                      <div>
                        <div className="font-semibold text-white">
                          Question {q.questionNumber}
                        </div>
                        <div className="text-sm text-gray-300">
                          {q.year} {q.season} • Paper {q.paper}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {q.topics.map((topic: string) => (
                        <span
                          key={topic}
                          className="px-3 py-1 bg-blue-900 text-blue-300 border border-blue-500 rounded-full text-sm font-medium"
                        >
                          Topic {topic}
                        </span>
                      ))}
                      {q.difficulty && (
                        <span className={`px-3 py-1 rounded-full text-sm font-medium border ${
                          q.difficulty === 'easy' ? 'bg-green-900 text-green-300 border-green-500' :
                          q.difficulty === 'medium' ? 'bg-yellow-900 text-yellow-300 border-yellow-500' :
                          'bg-red-900 text-red-300 border-red-500'
                        }`}>
                          {q.difficulty}
                        </span>
                      )}
                      {q.hasDiagram && (
                        <span className="px-3 py-1 bg-purple-900 text-purple-300 border border-purple-500 rounded-full text-sm">
                          📊 Diagram
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
