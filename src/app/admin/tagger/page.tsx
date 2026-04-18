"use client"
import { useEffect, useState, useCallback } from "react"

interface Topic { id: number; name: string }
interface PredictedTopic { id: number; name: string; confidence: number }
interface Question {
  id: number
  question_number: string
  text: string
  difficulty: number
  marks: number
  predicted_topics: PredictedTopic[]
}

const PAGE_SIZE = 50

export default function TaggerPage() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [allTopics, setAllTopics] = useState<Topic[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saveMsg, setSaveMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)

  // Filters + pagination
  const [offset, setOffset] = useState(0)
  const [untaggedOnly, setUntaggedOnly] = useState(false)
  const [minConf, setMinConf] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    setSaveMsg(null)
    try {
      const params = new URLSearchParams({
        offset: String(offset),
        limit: String(PAGE_SIZE),
        untagged: String(untaggedOnly),
        minConf: String(minConf),
      })
      const res = await fetch(`/api/admin/tagger?${params}`)
      const data = await res.json()
      if (!res.ok) {
        setSaveMsg({ type: "err", text: data.error || "Failed to load" })
        return
      }
      setQuestions(data.questions || [])
      setAllTopics(data.topics || [])
      setTotal(data.total || 0)
    } finally {
      setLoading(false)
    }
  }, [offset, untaggedOnly, minConf])

  useEffect(() => { load() }, [load])

  async function saveTags(qId: number, topicIds: number[]) {
    setSaveMsg(null)
    setSavingId(qId)
    const res = await fetch("/api/admin/tagger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: qId, topic_ids: topicIds }),
    })
    const data = await res.json()
    if (res.ok) {
      setSaveMsg({ type: "ok", text: `Saved ${data.tagged} tag(s) for question ${qId}` })
    } else {
      setSaveMsg({ type: "err", text: data.error || "Save failed" })
    }
    setSavingId(null)
  }

  const containerStyle: React.CSSProperties = { padding: "2rem", maxWidth: "900px" }
  const pageCount = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div style={containerStyle}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>
        Question Tagger (QA)
      </h1>
      <p style={{ fontSize: "0.875rem", color: "var(--gm-text-3)", marginBottom: "1.5rem" }}>
        Review auto-tagged questions, fix topics, and adjust difficulty.
      </p>

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap", marginBottom: "1.25rem", padding: "0.875rem 1rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.625rem" }}>
        <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", color: "var(--gm-text-2)", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={untaggedOnly}
            onChange={e => { setUntaggedOnly(e.target.checked); setOffset(0) }}
          />
          Untagged only
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", color: "var(--gm-text-2)" }}>
          Min confidence &lt;
          <select
            value={minConf}
            onChange={e => { setMinConf(parseFloat(e.target.value)); setOffset(0) }}
            style={{ background: "var(--gm-bg)", border: "1px solid var(--gm-border)", borderRadius: "0.375rem", padding: "0.2rem 0.4rem", color: "var(--gm-text)", fontSize: "0.78rem" }}
          >
            <option value={0}>All</option>
            <option value={0.5}>50%</option>
            <option value={0.7}>70%</option>
            <option value={0.9}>90%</option>
          </select>
        </label>
        <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginLeft: "auto" }}>
          {total} total questions
        </span>
        <button
          onClick={() => load()}
          style={{ padding: "0.3rem 0.75rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.375rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: "pointer" }}
        >
          Refresh
        </button>
      </div>

      {saveMsg && (
        <div style={{
          marginBottom: "1rem", padding: "0.625rem 0.875rem", borderRadius: "0.5rem", fontSize: "0.8rem",
          background: saveMsg.type === "ok" ? "#22c55e10" : "#ef444410",
          border: `1px solid ${saveMsg.type === "ok" ? "#22c55e30" : "#ef444430"}`,
          color: saveMsg.type === "ok" ? "#22c55e" : "#ef4444",
        }}>
          {saveMsg.text}
        </div>
      )}

      {loading ? (
        <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading questions…</div>
      ) : questions.length === 0 ? (
        <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>No questions match the current filters.</div>
      ) : (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {questions.map(q => (
              <QuestionCard
                key={q.id}
                question={q}
                allTopics={allTopics}
                onSave={saveTags}
                saving={savingId === q.id}
              />
            ))}
          </div>

          {/* Pagination */}
          {pageCount > 1 && (
            <div style={{ marginTop: "1.5rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.75rem" }}>
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                style={{ padding: "0.4rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: offset === 0 ? "not-allowed" : "pointer", opacity: offset === 0 ? 0.4 : 1 }}
              >
                ← Prev
              </button>
              <span style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
                Page {currentPage} of {pageCount}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                style={{ padding: "0.4rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: offset + PAGE_SIZE >= total ? "not-allowed" : "pointer", opacity: offset + PAGE_SIZE >= total ? 0.4 : 1 }}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function QuestionCard({ question, allTopics, onSave, saving }: {
  question: Question
  allTopics: Topic[]
  onSave: (qId: number, topicIds: number[]) => Promise<void>
  saving: boolean
}) {
  const [selected, setSelected] = useState<number[]>(question.predicted_topics.map(t => t.id))

  function toggle(id: number) {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  return (
    <div style={{
      background: "var(--gm-surface)",
      border: "1px solid var(--gm-border)",
      borderRadius: "0.625rem",
      padding: "1rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
        <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>
          {question.question_number} · {question.marks} marks · Difficulty {question.difficulty}
        </span>
        <button
          onClick={() => { void onSave(question.id, selected) }}
          disabled={saving}
          style={{
            padding: "0.25rem 0.75rem",
            background: saving ? "var(--gm-border)" : "#22c55e",
            color: saving ? "var(--gm-text-3)" : "#000",
            border: "none", borderRadius: "0.375rem", fontSize: "0.75rem", fontWeight: 600,
            cursor: saving ? "not-allowed" : "pointer", opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>

      <p style={{ fontSize: "0.8rem", color: "var(--gm-text-2)", lineHeight: 1.5, marginBottom: "0.75rem", whiteSpace: "pre-wrap" }}>
        {question.text.slice(0, 300)}{question.text.length > 300 ? "…" : ""}
      </p>

      {question.predicted_topics.length > 0 && (
        <div style={{ marginBottom: "0.625rem" }}>
          <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>
            Auto-tagged ({question.predicted_topics.length}):
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
            {question.predicted_topics.map(t => (
              <span
                key={t.id}
                style={{
                  padding: "0.15rem 0.5rem", borderRadius: "999px", fontSize: "0.7rem",
                  background: "#f59e0b20", color: "#f59e0b", border: "1px solid #f59e0b30",
                }}
              >
                {t.name} ({(t.confidence * 100).toFixed(0)}%)
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", display: "block", marginBottom: "0.25rem" }}>
          Select correct topics ({selected.length} selected):
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
          {allTopics.map(t => (
            <button
              key={t.id}
              onClick={() => toggle(t.id)}
              style={{
                padding: "0.15rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.7rem",
                background: selected.includes(t.id) ? "var(--gm-text)" : "var(--gm-bg)",
                color: selected.includes(t.id) ? "var(--gm-bg)" : "var(--gm-text-3)",
                border: `1px solid ${selected.includes(t.id) ? "var(--gm-text)" : "var(--gm-border)"}`,
                cursor: "pointer",
              }}
            >
              {t.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
