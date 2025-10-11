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

export default function TaggerPage() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [allTopics, setAllTopics] = useState<{id: number; name: string}[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const { data: qs } = await supabase
        .from('questions')
        .select('id, question_number, text, difficulty, marks, question_topics(topic_id, confidence, topics(id, name))')
        .order('id', { ascending: false })
        .limit(50)
      
      const { data: topics } = await supabase.from('topics').select('id, name').order('name')
      setAllTopics(topics || [])

      const mapped = (qs || []).map(q => {
        const question_topics = q.question_topics as Array<{
          topic_id: number
          confidence: number
          topics: Array<{ id: number; name: string }>
        }>
        return {
          ...q,
          predicted_topics: (question_topics || []).map(qt => ({
            id: qt.topics[0]?.id || 0,
            name: qt.topics[0]?.name || 'Unknown',
            confidence: qt.confidence
          }))
        }
      })
      setQuestions(mapped)
      setLoading(false)
    }
    load()
  }, [])

  async function saveTags(qId: number, topicIds: number[]) {
    // Delete old, insert new
    await supabase.from('question_topics').delete().eq('question_id', qId)
    if (topicIds.length) {
      await supabase.from('question_topics').insert(topicIds.map(tid => ({ question_id: qId, topic_id: tid, confidence: 1.0 })))
    }
    alert('Saved!')
  }

  if (loading) return <div className="min-h-screen text-white p-6">Loading...</div>

  return (
    <main className="min-h-screen text-white p-6 bg-black">
      <h1 className="text-2xl font-semibold mb-6">Admin: Question Tagger (QA)</h1>
      <p className="text-sm text-white/70 mb-8">Review auto-tagged questions, fix topics, and adjust difficulty.</p>

      <div className="space-y-6">
        {questions.map(q => (
          <QuestionCard key={q.id} question={q} allTopics={allTopics} onSave={saveTags} />
        ))}
      </div>
    </main>
  )
}

function QuestionCard({ question, allTopics, onSave }: {
  question: Question
  allTopics: {id: number; name: string}[]
  onSave: (qId: number, topicIds: number[]) => void
}) {
  const [selected, setSelected] = useState<number[]>(question.predicted_topics.map(t => t.id))

  function toggle(id: number) {
    setSelected(prev => prev.includes(id) ? prev.filter(x=>x!==id) : [...prev, id])
  }

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10">
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs text-white/70">{question.question_number} • {question.marks} marks • Diff {question.difficulty}</span>
        <button onClick={() => onSave(question.id, selected)} className="rounded bg-emerald-500 text-black px-3 py-1 text-xs font-medium hover:bg-emerald-600">Save</button>
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
