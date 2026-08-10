"use client"

/**
 * Phase 4: workbook section verification.
 *
 * The classifier is roughly 80% right and its self-reported confidence carries
 * no signal (0.858 mean where two models agreed, 0.827 where they disagreed).
 * So every question is confirmed by a human before it can appear in the book —
 * the RLS policy on workbook_questions only exposes verified rows.
 *
 * The screen is built for speed, because the cost is your time: the question
 * PDF renders on the left, the proposal and its alternatives on the right, and
 * the whole loop is keyboard-driven. The queue is ordered by two-model
 * disagreement so the ~54 genuinely hard questions come first and the ~250
 * confirm-and-move-on ones come last.
 *
 * `/admin/tagger` already exists but is text-only, which does not work for
 * maths: diagrams and notation carry the classification.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"

interface Chapter {
  id: string
  number: number
  title: string
}

interface Section {
  id: string
  chapter_id: string
  number: number
  title: string
}

interface Question {
  id: string
  slug: string
  section_id: string
  proposed_section_id: string | null
  review_priority: "disputed" | "same_chapter" | "unconfirmed" | "agreed" | null
  classifier_confidence: number | null
  secondary_section_ids: string[] | null
  marks: number
  difficulty: string | null
  qp_pdf_url: string | null
  ms_pdf_url: string | null
  text_status: string | null
  source_paper_key: string
  source_question_number: number
  verified_at: string | null
}

const PRIORITY_LABEL: Record<string, string> = {
  disputed: "Models disagree",
  same_chapter: "Same chapter, different section",
  unconfirmed: "No second opinion",
  agreed: "Both models agree",
}

const PRIORITY_COLOR: Record<string, string> = {
  disputed: "#b91c1c",
  same_chapter: "#b45309",
  unconfirmed: "#4b5563",
  agreed: "#15803d",
}

export default function WorkbookVerifyPage() {
  const [subjectId, setSubjectId] = useState("")
  const [subjects, setSubjects] = useState<{ id: string; code: string; name: string }[]>([])
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const [queue, setQueue] = useState<Question[]>([])
  const [index, setIndex] = useState(0)
  const [remainingTotal, setRemainingTotal] = useState(0)
  const [verifiedThisSession, setVerifiedThisSession] = useState(0)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [picker, setPicker] = useState("")
  const [showMarkScheme, setShowMarkScheme] = useState(false)
  const pickerRef = useRef<HTMLInputElement>(null)

  const current = queue[index]

  const sectionById = useMemo(() => {
    const map = new Map<string, Section>()
    for (const s of sections) map.set(s.id, s)
    return map
  }, [sections])

  const chapterById = useMemo(() => {
    const map = new Map<string, Chapter>()
    for (const c of chapters) map.set(c.id, c)
    return map
  }, [chapters])

  const codeOf = useCallback(
    (sectionId: string | null | undefined) => {
      if (!sectionId) return null
      const section = sectionById.get(sectionId)
      if (!section) return null
      const chapter = chapterById.get(section.chapter_id)
      if (!chapter) return null
      return `${chapter.number}.${section.number}`
    },
    [sectionById, chapterById]
  )

  const titleOf = useCallback(
    (sectionId: string | null | undefined) =>
      sectionId ? (sectionById.get(sectionId)?.title ?? null) : null,
    [sectionById]
  )

  const sectionByCode = useMemo(() => {
    const map = new Map<string, Section>()
    for (const s of sections) {
      const chapter = chapterById.get(s.chapter_id)
      if (chapter) map.set(`${chapter.number}.${s.number}`, s)
    }
    return map
  }, [sections, chapterById])

  useEffect(() => {
    fetch("/api/subjects")
      .then((r) => r.json())
      .then((d) => {
        const list = (d.subjects ?? d ?? []) as { id: string; code: string; name: string }[]
        setSubjects(list)
        const fpm = list.find((s) => s.code === "4PM1")
        if (fpm) setSubjectId(fpm.id)
      })
      .catch(() => setMessage("Could not load subjects"))
  }, [])

  const loadQueue = useCallback(async () => {
    if (!subjectId) return
    setLoading(true)
    setMessage(null)
    try {
      const res = await fetch(`/api/admin/workbook/queue?subjectId=${subjectId}&limit=80`)
      const data = await res.json()
      if (!res.ok) {
        setMessage(data.error || "Failed to load the queue")
        return
      }
      setChapters(data.chapters ?? [])
      setSections(data.sections ?? [])
      setQueue(data.questions ?? [])
      setRemainingTotal(data.totalUnverified ?? 0)
      setIndex(0)
    } catch {
      setMessage("Failed to load the queue")
    } finally {
      setLoading(false)
    }
  }, [subjectId])

  useEffect(() => {
    void loadQueue()
  }, [loadQueue])

  const advance = useCallback(() => {
    setPicker("")
    setShowMarkScheme(false)
    setIndex((i) => {
      const next = i + 1
      if (next >= queue.length) {
        void loadQueue()
        return 0
      }
      return next
    })
  }, [queue.length, loadQueue])

  const submit = useCallback(
    async (sectionId?: string) => {
      if (!current || saving) return
      setSaving(true)
      try {
        const res = await fetch("/api/admin/workbook/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ questionId: current.id, sectionId }),
        })
        const data = await res.json()
        if (!res.ok) {
          setMessage(data.error || "Could not save")
          return
        }
        setVerifiedThisSession((n) => n + 1)
        setRemainingTotal(data.remainingUnverified ?? remainingTotal - 1)
        advance()
      } catch {
        setMessage("Could not save")
      } finally {
        setSaving(false)
      }
    },
    [current, saving, advance, remainingTotal]
  )

  const applyPicker = useCallback(() => {
    const target = sectionByCode.get(picker.trim())
    if (!target) {
      setMessage(`No section "${picker.trim()}"`)
      return
    }
    void submit(target.id)
  }, [picker, sectionByCode, submit])

  // Keyboard loop. Typing in the picker must not trigger the shortcuts.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return

      if (event.key === "Enter" || event.key === "a") {
        event.preventDefault()
        void submit()
      } else if (event.key === "r" && current?.proposed_section_id) {
        event.preventDefault()
        void submit(current.proposed_section_id)
      } else if (event.key === "s") {
        event.preventDefault()
        advance()
      } else if (event.key === "m") {
        event.preventDefault()
        setShowMarkScheme((v) => !v)
      } else if (event.key === "ArrowLeft") {
        event.preventDefault()
        setIndex((i) => Math.max(0, i - 1))
      } else if (event.key === "ArrowRight") {
        event.preventDefault()
        advance()
      } else if (event.key === "/") {
        event.preventDefault()
        pickerRef.current?.focus()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [submit, advance, current])

  const priority = current?.review_priority ?? "unconfirmed"
  const proposedCode = codeOf(current?.proposed_section_id)
  const assignedCode = codeOf(current?.section_id)

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1500, margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ display: "flex", alignItems: "baseline", gap: 16, flexWrap: "wrap", marginBottom: 18 }}>
        <h1 style={{ fontSize: 20, fontWeight: 650, margin: 0 }}>Workbook verification</h1>
        <select
          value={subjectId}
          onChange={(e) => setSubjectId(e.target.value)}
          style={{ padding: "5px 8px", border: "1px solid #d4d4d8", borderRadius: 6 }}
        >
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} — {s.name}
            </option>
          ))}
        </select>
        <span style={{ marginLeft: "auto", fontSize: 13, color: "#52525b" }}>
          <strong>{remainingTotal}</strong> unverified · <strong>{verifiedThisSession}</strong> done this session
        </span>
      </header>

      {message && (
        <p style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", padding: "8px 12px", borderRadius: 6, fontSize: 13 }}>
          {message}
        </p>
      )}

      {loading && <p style={{ color: "#71717a" }}>Loading…</p>}

      {!loading && !current && (
        <p style={{ color: "#15803d", fontWeight: 600 }}>
          Nothing left to verify for this subject.
        </p>
      )}

      {current && (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 380px", gap: 20, alignItems: "start" }}>
          <div style={{ border: "1px solid #e4e4e7", borderRadius: 8, overflow: "hidden", background: "#fff" }}>
            <div style={{ padding: "8px 12px", borderBottom: "1px solid #e4e4e7", display: "flex", gap: 12, fontSize: 12, color: "#52525b" }}>
              <strong style={{ color: "#18181b" }}>{current.slug}</strong>
              <span>{current.source_paper_key} Q{current.source_question_number}</span>
              <span>{current.marks} marks</span>
              <span>{current.difficulty}</span>
              {current.text_status === "needs_vision" && (
                <span style={{ color: "#b45309" }}>scanned — classified from the image</span>
              )}
              <button
                onClick={() => setShowMarkScheme((v) => !v)}
                disabled={!current.ms_pdf_url}
                style={{ marginLeft: "auto", fontSize: 12, padding: "2px 8px", cursor: current.ms_pdf_url ? "pointer" : "not-allowed" }}
              >
                {showMarkScheme ? "Question (m)" : "Mark scheme (m)"}
              </button>
            </div>
            {(() => {
              const url = showMarkScheme ? current.ms_pdf_url : current.qp_pdf_url
              if (!url) {
                return <p style={{ padding: 24, color: "#71717a" }}>No mark scheme available for this question.</p>
              }
              return (
                <iframe
                  key={url}
                  src={`${url}#toolbar=0&view=FitH`}
                  title={current.slug}
                  style={{ width: "100%", height: "78vh", border: "none", display: "block" }}
                />
              )
            })()}
          </div>

          <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ border: `1px solid ${PRIORITY_COLOR[priority]}`, borderLeftWidth: 4, borderRadius: 6, padding: "10px 12px" }}>
              <div style={{ fontSize: 11, letterSpacing: ".08em", textTransform: "uppercase", color: PRIORITY_COLOR[priority], fontWeight: 600 }}>
                {PRIORITY_LABEL[priority]}
              </div>
              {current.classifier_confidence !== null && (
                <div style={{ fontSize: 11, color: "#71717a", marginTop: 4 }}>
                  self-reported confidence {current.classifier_confidence.toFixed(2)} — not a reliable signal
                </div>
              )}
            </div>

            <div style={{ border: "1px solid #e4e4e7", borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#71717a", textTransform: "uppercase", letterSpacing: ".06em" }}>Assigned</div>
              <div style={{ fontSize: 15, fontWeight: 600, marginTop: 2 }}>
                {assignedCode} {titleOf(current.section_id)}
              </div>

              {proposedCode && proposedCode !== assignedCode && (
                <>
                  <div style={{ fontSize: 11, color: "#71717a", textTransform: "uppercase", letterSpacing: ".06em", marginTop: 12 }}>
                    Second model says
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 600, marginTop: 2 }}>
                    {proposedCode} {titleOf(current.proposed_section_id)}
                  </div>
                </>
              )}

              {(current.secondary_section_ids?.length ?? 0) > 0 && (
                <div style={{ fontSize: 12, color: "#52525b", marginTop: 12 }}>
                  also draws on:{" "}
                  {current.secondary_section_ids!.map((id) => codeOf(id)).filter(Boolean).join(", ")}
                </div>
              )}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button
                onClick={() => void submit()}
                disabled={saving}
                style={{ padding: "10px 12px", fontWeight: 600, background: "#15803d", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
              >
                Accept {assignedCode} &nbsp;<kbd>Enter</kbd>
              </button>

              {proposedCode && proposedCode !== assignedCode && (
                <button
                  onClick={() => void submit(current.proposed_section_id!)}
                  disabled={saving}
                  style={{ padding: "10px 12px", fontWeight: 600, background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
                >
                  Use {proposedCode} instead &nbsp;<kbd>r</kbd>
                </button>
              )}

              <div style={{ display: "flex", gap: 6 }}>
                <input
                  ref={pickerRef}
                  value={picker}
                  onChange={(e) => setPicker(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") applyPicker()
                    if (e.key === "Escape") (e.target as HTMLInputElement).blur()
                  }}
                  placeholder="Reassign — type 9.4 then Enter  (/)"
                  style={{ flex: 1, padding: "8px 10px", border: "1px solid #d4d4d8", borderRadius: 6, fontSize: 13 }}
                />
                <button onClick={applyPicker} disabled={saving} style={{ padding: "8px 12px" }}>
                  Go
                </button>
              </div>

              <button onClick={advance} style={{ padding: "8px 12px", background: "none", border: "1px solid #d4d4d8", borderRadius: 6, cursor: "pointer" }}>
                Skip &nbsp;<kbd>s</kbd>
              </button>
            </div>

            <details style={{ fontSize: 12, color: "#52525b" }}>
              <summary style={{ cursor: "pointer" }}>All sections</summary>
              <div style={{ maxHeight: 260, overflowY: "auto", marginTop: 8 }}>
                {chapters.map((chapter) => (
                  <div key={chapter.id} style={{ marginBottom: 8 }}>
                    <div style={{ fontWeight: 600, color: "#18181b" }}>
                      {chapter.number}. {chapter.title}
                    </div>
                    {sections
                      .filter((s) => s.chapter_id === chapter.id)
                      .map((s) => (
                        <button
                          key={s.id}
                          onClick={() => void submit(s.id)}
                          style={{ display: "block", width: "100%", textAlign: "left", padding: "3px 6px", border: "none", background: "none", cursor: "pointer", fontSize: 12 }}
                        >
                          {chapter.number}.{s.number} {s.title}
                        </button>
                      ))}
                  </div>
                ))}
              </div>
            </details>

            <p style={{ fontSize: 11, color: "#a1a1aa", lineHeight: 1.6 }}>
              <kbd>Enter</kbd> accept · <kbd>r</kbd> use second opinion · <kbd>/</kbd> reassign ·{" "}
              <kbd>m</kbd> mark scheme · <kbd>s</kbd> skip · <kbd>←</kbd> <kbd>→</kbd> move
            </p>
          </aside>
        </div>
      )}
    </div>
  )
}
