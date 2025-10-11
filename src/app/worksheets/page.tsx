"use client"
import { useEffect, useState } from 'react'

interface Subject {
  id: string
  code: string
  name: string
  level: string
}

interface Topic {
  id: string
  code: string
  name: string
}

interface WorksheetItem {
  position: number
  questionId: string
  questionNumber: string
  text: string
  marks?: number
  difficulty: number
  source: string
  markscheme?: string
}

interface WorksheetResponse {
  worksheetId: string
  subject: { code: string; name: string; level: string }
  items: WorksheetItem[]
  error?: string
}

export default function WorksheetsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedSubjectCode, setSelectedSubjectCode] = useState<string>('')
  const [selectedTopicCodes, setSelectedTopicCodes] = useState<string[]>([])
  const [selectedDifficulties, setSelectedDifficulties] = useState<number[]>([1, 2, 3])
  const [questionCount, setQuestionCount] = useState(10)
  const [includeMarkscheme, setIncludeMarkscheme] = useState(false)
  const [worksheet, setWorksheet] = useState<WorksheetResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load subjects on mount
  useEffect(() => {
    async function loadSubjects() {
      try {
        const res = await fetch('/api/subjects')
        const data = await res.json()
        setSubjects(data || [])
      } catch (err) {
        console.error('Failed to load subjects:', err)
      }
    }
    loadSubjects()
  }, [])

  // Load topics when subject changes
  useEffect(() => {
    async function loadTopics() {
      if (!selectedSubjectCode) {
        setTopics([])
        setSelectedTopicCodes([])
        return
      }

      try {
        const subject = subjects.find(s => s.code === selectedSubjectCode)
        if (!subject) {
          console.log('Subject not found for code:', selectedSubjectCode)
          return
        }

        console.log('Loading topics for subject:', subject)
        const res = await fetch(`/api/topics?subjectId=${subject.id}`)
        const data = await res.json()
        console.log('Topics loaded:', data)
        setTopics(data || [])
      } catch (err) {
        console.error('Failed to load topics:', err)
      }
    }
    loadTopics()
  }, [selectedSubjectCode, subjects])

  function toggleTopic(code: string) {
    setSelectedTopicCodes(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    )
  }

  function toggleDifficulty(diff: number) {
    setSelectedDifficulties(prev =>
      prev.includes(diff)
        ? prev.filter(d => d !== diff)
        : [...prev, diff]
    )
  }

  async function handleGenerate() {
    if (!selectedSubjectCode) {
      setError('Please select a subject')
      return
    }

    setLoading(true)
    setError(null)
    setWorksheet(null)

    try {
      const res = await fetch('/api/worksheets/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subjectCode: selectedSubjectCode,
          topicCodes: selectedTopicCodes.length > 0 ? selectedTopicCodes : undefined,
          difficulties: selectedDifficulties,
          count: questionCount,
          includeMarkscheme,
          shuffle: true
        })
      })

      const data = await res.json()

      if (!res.ok || data.error) {
        setError(data.error || 'Failed to generate worksheet')
      } else {
        setWorksheet(data)
      }
    } catch (err) {
      console.error('Generate error:', err)
      setError('Network error - please try again')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">
          📝 Worksheet Generator
        </h1>

        {/* Filters */}
        <div className="bg-white/5 border border-white/10 rounded-lg shadow-md p-6 mb-6 space-y-6">
          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Subject
            </label>
            <select
              value={selectedSubjectCode}
              onChange={e => setSelectedSubjectCode(e.target.value)}
              className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="" className="bg-gray-900 text-white">Select a subject...</option>
              {subjects.map(s => (
                <option key={s.id} value={s.code} className="bg-gray-900 text-white">
                  {s.level} {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>

          {/* Topics */}
          {selectedSubjectCode && (
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Topics (optional - leave empty for all) {topics.length > 0 && `- ${topics.length} available`}
              </label>
              {topics.length === 0 ? (
                <div className="text-sm text-white/70 py-4">
                  Loading topics...
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {topics.map(t => (
                    <label key={t.id} className="flex items-center space-x-2 cursor-pointer hover:bg-white/5 p-2 rounded">
                      <input
                        type="checkbox"
                        checked={selectedTopicCodes.includes(t.code)}
                        onChange={() => toggleTopic(t.code)}
                        className="rounded text-blue-600 focus:ring-blue-500 bg-white/10 border-white/20"
                      />
                      <span className="text-sm text-white">{t.name}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Difficulty */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Difficulty
            </label>
            <div className="flex gap-4">
              {[1, 2, 3].map(diff => (
                <label key={diff} className="flex items-center space-x-2 cursor-pointer hover:bg-white/5 p-2 rounded">
                  <input
                    type="checkbox"
                    checked={selectedDifficulties.includes(diff)}
                    onChange={() => toggleDifficulty(diff)}
                    className="rounded text-blue-600 focus:ring-blue-500 bg-white/10 border-white/20"
                  />
                  <span className="text-sm text-white">
                    {diff === 1 ? 'Easy' : diff === 2 ? 'Medium' : 'Hard'}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Count */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Number of Questions: {questionCount}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={questionCount}
              onChange={e => setQuestionCount(parseInt(e.target.value))}
              className="w-full accent-blue-600"
            />
          </div>

          {/* Include Markscheme */}
          <div>
            <label className="flex items-center space-x-2 cursor-pointer hover:bg-white/5 p-2 rounded">
              <input
                type="checkbox"
                checked={includeMarkscheme}
                onChange={e => setIncludeMarkscheme(e.target.checked)}
                className="rounded text-blue-600 focus:ring-blue-500 bg-white/10 border-white/20"
              />
              <span className="text-sm text-white">Include markscheme</span>
            </label>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={loading || !selectedSubjectCode}
            className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Generating...' : 'Generate Worksheet'}
          </button>

          {error && (
            <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Results */}
        {worksheet && worksheet.items.length > 0 && (
          <div className="bg-white/5 border border-white/10 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {worksheet.subject.level} {worksheet.subject.name}
                </h2>
                <p className="text-sm text-white/70">
                  {worksheet.items.length} questions
                </p>
              </div>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors"
              >
                🖨️ Print
              </button>
            </div>

            <div className="space-y-8">
              {worksheet.items.map(item => (
                <div key={item.position} className="border-b border-white/10 pb-6 last:border-b-0">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-white">
                        {item.questionNumber}
                      </span>
                      {item.marks && (
                        <span className="text-sm text-white/70">
                          [{item.marks} {item.marks === 1 ? 'mark' : 'marks'}]
                        </span>
                      )}
                      <span className={`text-xs px-2 py-1 rounded ${
                        item.difficulty === 1 
                          ? 'bg-green-500/20 text-green-300'
                          : item.difficulty === 2
                          ? 'bg-yellow-500/20 text-yellow-300'
                          : 'bg-red-500/20 text-red-300'
                      }`}>
                        {item.difficulty === 1 ? 'Easy' : item.difficulty === 2 ? 'Medium' : 'Hard'}
                      </span>
                    </div>
                    <span className="text-xs text-white/50">
                      {item.source}
                    </span>
                  </div>

                  <div className="text-white whitespace-pre-wrap mb-4">
                    {item.text}
                  </div>

                  {item.markscheme && (
                    <details className="mt-4">
                      <summary className="cursor-pointer text-sm font-medium text-blue-400 hover:text-blue-300">
                        Show markscheme
                      </summary>
                      <div className="mt-2 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-white/90 whitespace-pre-wrap">
                        {item.markscheme}
                      </div>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style jsx global>{`
        @media print {
          .no-print {
            display: none !important;
          }
        }
      `}</style>
    </div>
  )
}
