'use client';

import { useState, useEffect } from 'react';

interface Question {
  id: string;
  questionNumber: string;
  topicCode: string;
  difficulty: string;
  confidence: number;
  pagePdfUrl: string;
  msPdfUrl?: string;
  hasDiagram: boolean;
  pageCount: number;
  year: number;
  season: string;
  paper: string;
  board: string;
  level: string;
  subject: string;
}

const TOPICS = [
  { code: '1', name: 'Forces and motion' },
  { code: '2', name: 'Electricity' },
  { code: '3', name: 'Waves' },
  { code: '4', name: 'Energy resources' },
  { code: '5', name: 'Solids, liquids and gases' },
  { code: '6', name: 'Magnetism and electromagnetism' },
  { code: '7', name: 'Radioactivity and particles' },
  { code: '8', name: 'Astrophysics' },
];

export default function BrowseQuestionsPage() {
  const [selectedTopic, setSelectedTopic] = useState<string>('1');
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://tybaetnvnfgniotdfxze.supabase.co';

  useEffect(() => {
    if (selectedTopic) {
      loadQuestions(selectedTopic);
    }
  }, [selectedTopic]);

  const loadQuestions = async (topicCode: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/questions?topic_code=${topicCode}&limit=20`);
      const data = await response.json();

      if (response.ok) {
        setQuestions(data.questions || []);
      } else {
        setError(data.error || 'Failed to load questions');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setLoading(false);
    }
  };

  const selectedTopicName = TOPICS.find((t) => t.code === selectedTopic)?.name || '';

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Browse Questions by Topic</h1>

        {/* Topic Selector */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Select Topic</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {TOPICS.map((topic) => (
              <button
                key={topic.code}
                onClick={() => setSelectedTopic(topic.code)}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedTopic === topic.code
                    ? 'border-blue-500 bg-blue-50 text-blue-700 font-semibold'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-sm text-gray-500">Topic {topic.code}</div>
                <div className="font-medium">{topic.name}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Questions List */}
        {loading && (
          <div className="text-center py-12">
            <div className="text-gray-600">Loading questions...</div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <div className="text-red-800 font-semibold">Error</div>
            <div className="text-red-600">{error}</div>
          </div>
        )}

        {!loading && !error && questions.length === 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <div className="text-yellow-800 font-semibold mb-2">No Questions Found</div>
            <div className="text-yellow-600">
              No questions available for Topic {selectedTopic}: {selectedTopicName}
            </div>
            <div className="text-sm text-yellow-600 mt-2">
              Run the ingestion pipeline to add questions.
            </div>
          </div>
        )}

        {!loading && !error && questions.length > 0 && (
          <div>
            <div className="mb-4 text-gray-600">
              Showing {questions.length} questions for <strong>Topic {selectedTopic}: {selectedTopicName}</strong>
            </div>

            <div className="space-y-6">
              {questions.map((q) => (
                <div key={q.id} className="bg-white rounded-lg shadow-lg overflow-hidden">
                  {/* Question Header */}
                  <div className="bg-gray-100 px-6 py-4 border-b">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm text-gray-500">
                          {q.year} {q.season} • {q.paper} • Q{q.questionNumber}
                        </span>
                        <div className="flex items-center gap-3 mt-1">
                          <span className={`px-3 py-1 rounded text-sm font-medium ${
                            q.difficulty === 'easy' ? 'bg-green-100 text-green-700' :
                            q.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {q.difficulty}
                          </span>
                          {q.hasDiagram && (
                            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm">
                              📊 Has Diagram
                            </span>
                          )}
                          <span className="text-xs text-gray-500">
                            Confidence: {(q.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {q.msPdfUrl && (
                          <a
                            href={`${supabaseUrl}/storage/v1/object/public/question-pdfs/${q.msPdfUrl}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                          >
                            📝 Mark Scheme
                          </a>
                        )}
                        <a
                          href={`${supabaseUrl}/storage/v1/object/public/question-pdfs/${q.pagePdfUrl}`}
                          download
                          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                          ⬇️ Download
                        </a>
                      </div>
                    </div>
                  </div>

                  {/* Question PDF */}
                  <div className="p-6">
                    <iframe
                      src={`${supabaseUrl}/storage/v1/object/public/question-pdfs/${q.pagePdfUrl}#view=FitH`}
                      width="100%"
                      height="600px"
                      className="border rounded"
                      title={`Question ${q.questionNumber}`}
                    />
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
