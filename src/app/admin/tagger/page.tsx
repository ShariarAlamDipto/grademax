"use client"
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabaseClient'

interface Question {
  id: number
  question_number: string
  text: string
  difficulty: number
  marks: number
  predicted_topics: { id: number; name: string; confidence: number }[]
}

interface RawTopic {
  id: number
  name: string
}

interface RawQuestionTopic {
  topic_id: number
  confidence: number
  topics: RawTopic | RawTopic[] | null
}

interface RawQuestion {
  id: number
  question_number: string
  text: string
  difficulty: number
  marks: number
  question_topics: RawQuestionTopic[] | null
}

export default function TaggerPage() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [allTopics, setAllTopics] = useState<{id: number; name: string}[]>([])
  const [loading, setLoading] = useState(true)
  const [saveMsg, setSaveMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [{ data: qs, error: qErr }, { data: topics, error: tErr }] = await Promise.all([
          supabase
            .from('questions')
            .select('id, question_number, text, difficulty, marks, question_topics(topic_id, confidence, topics(id, name))')
            .order('id', { ascending: false })
            .limit(50),
          supabase.from('topics').select('id, name').order('name'),
        ])

        if (qErr || tErr) {
          setSaveMsg({ type: 'err', text: qErr?.message || tErr?.message || 'Failed to load tagger data' })
          setQuestions([])
          setAllTopics([])
          return
        }

        setAllTopics(topics || [])

        const mapped = ((qs || []) as RawQuestion[]).map(q => {
          const predictedTopics = (q.question_topics || [])
            .map(qt => {
              const topic = Array.isArray(qt.topics) ? qt.topics[0] : qt.topics
              if (!topic?.id || !topic?.name) {
                return null
              }
              return {
                id: topic.id,
                name: topic.name,
                confidence: qt.confidence,
              }
            })
            .filter((topic): topic is { id: number; name: string; confidence: number } => topic !== null)

          return {
            id: q.id,
            question_number: q.question_number,
            text: q.text,
            difficulty: q.difficulty,
            marks: q.marks,
            predicted_topics: predictedTopics,
          }
        })

        setQuestions(mapped)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  async function saveTags(qId: number, topicIds: number[]) {
    setSaveMsg(null)
    setSavingId(qId)
    const { error: deleteError } = await supabase.from('question_topics').delete().eq('question_id', qId)
    if (deleteError) {
      setSaveMsg({ type: 'err', text: deleteError.message })
      setSavingId(null)
      return
    }

    if (topicIds.length) {
      const { error: insertError } = await supabase
        .from('question_topics')
        .insert(topicIds.map(tid => ({ question_id: qId, topic_id: tid, confidence: 1.0 })))
      if (insertError) {
        setSaveMsg({ type: 'err', text: insertError.message })
        setSavingId(null)
        return
      }
    }

    setSaveMsg({ type: 'ok', text: 'Tags saved successfully' })
    setSavingId(null)
  }

  if (loading) return <div className="min-h-screen text-white p-6">Loading...</div>

  return (
    <main className="min-h-screen text-white p-6 bg-black">
      <h1 className="text-2xl font-semibold mb-6">Admin: Question Tagger (QA)</h1>
      <p className="text-sm text-white/70 mb-8">Review auto-tagged questions, fix topics, and adjust difficulty.</p>

      {saveMsg && (
        <div className={`mb-4 rounded border px-3 py-2 text-sm ${saveMsg.type === 'ok' ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-rose-500/40 bg-rose-500/10 text-rose-300'}`}>
          {saveMsg.text}
        </div>
      )}

      <div className="space-y-6">
        {questions.map(q => (
          <QuestionCard key={q.id} question={q} allTopics={allTopics} onSave={saveTags} saving={savingId === q.id} />
        ))}
      </div>
    </main>
  )
}

function QuestionCard({ question, allTopics, onSave, saving }: {
  question: Question
  allTopics: {id: number; name: string}[]
  onSave: (qId: number, topicIds: number[]) => Promise<void>
  saving: boolean
}) {
  const [selected, setSelected] = useState<number[]>(question.predicted_topics.map(t => t.id))

  function toggle(id: number) {
    setSelected(prev => prev.includes(id) ? prev.filter(x=>x!==id) : [...prev, id])
  }

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10">
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs text-white/70">{question.question_number} • {question.marks} marks • Diff {question.difficulty}</span>
        <button
          onClick={() => { void onSave(question.id, selected) }}
          disabled={saving}
          className="rounded bg-emerald-500 text-black px-3 py-1 text-xs font-medium hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
      <p className="text-sm leading-snug mb-3 whitespace-pre-wrap">{question.text.slice(0, 300)}...</p>
      
      <div className="mb-2">
        <span className="text-xs text-white/70">Predicted topics ({question.predicted_topics.length}):</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {question.predicted_topics.map(t => (
            <span key={t.id} className="px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
              {t.name} ({(t.confidence * 100).toFixed(0)}%)
            </span>
          ))}
        </div>
      </div>

      <div>
        <span className="text-xs text-white/70">All topics (select correct):</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {allTopics.map(t => (
            <button key={t.id} onClick={() => toggle(t.id)} className={`px-2 py-0.5 rounded text-xs border ${selected.includes(t.id)?'bg-white text-black border-white':'bg-white/10 border-white/10'}`}>
              {t.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
