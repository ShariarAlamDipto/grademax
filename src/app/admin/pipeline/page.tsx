"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

interface TopicGuardrails { include_when?: string; exclude_when?: string }
interface Topic {
  id: string; code: string; name: string; description: string
  keywords: string[]; guardrails?: TopicGuardrails
}
interface Subject { id: string; name: string; code: string; level: string; board: string }
interface PipelineStatus {
  papers: number; pages: number; pagesWithUrl: number; pagesClassified: number
  topicDistribution: Record<string, number>; difficultyDistribution: Record<string, number>
}
interface R2PaperGroup {
  groupKey: string; year: number; session: string; paperNumber: string
  r2QP: string | null; r2MS: string | null; inDb: boolean
  dbId: string | null; hasPdfUrl: boolean; hasMsUrl: boolean
}
interface R2ScanResult {
  subjectCode: string; subjectFolder: string; r2Count: number; dbCount: number
  comparison: R2PaperGroup[]
  dbOnly: Array<{ year: number; season: string; paperNumber: string }>
  stats: { inBoth: number; r2Only: number; dbOnly: number }
}
interface ClassifyState {
  running: boolean; cancelled: boolean
  processed: number; classified: number; errors: number; total: number
  startTime: number; done: boolean; lastError: string
}

type Step = "subject" | "spec" | "topics" | "status"
const STEPS: Step[] = ["subject", "spec", "topics", "status"]
const STEP_LABELS: Record<Step, string> = {
  subject: "1. Select Subject", spec: "2. Upload Specification",
  topics: "3. Review Topics", status: "4. Pipeline Status",
}

function fmtEta(ms: number): string {
  if (!isFinite(ms) || ms <= 0) return ""
  const s = Math.ceil(ms / 1000)
  if (s < 60) return `~${s}s`
  return `~${Math.ceil(s / 60)}m ${s % 60}s`
}

function pct(n: number, total: number) { return total === 0 ? 0 : Math.round((n / total) * 100) }

export default function PipelinePage() {
  const [step, setStep] = useState<Step>("subject")
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null)
  const [specText, setSpecText] = useState("")
  const [analyzing, setAnalyzing] = useState(false)
  const [topics, setTopics] = useState<Topic[]>([])
  const [editingTopicIdx, setEditingTopicIdx] = useState<number | null>(null)
  const [savingTopics, setSavingTopics] = useState(false)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(false)
  const [r2Scan, setR2Scan] = useState<R2ScanResult | null>(null)
  const [loadingR2, setLoadingR2] = useState(false)
  const [classify, setClassify] = useState<ClassifyState>({
    running: false, cancelled: false, processed: 0, classified: 0,
    errors: 0, total: 0, startTime: 0, done: false, lastError: "",
  })
  const [reclassify, setReclassify] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null)
  const [specPdfBase64, setSpecPdfBase64] = useState("")
  const [specPdfName, setSpecPdfName] = useState("")
  const [specInputMode, setSpecInputMode] = useState<"pdf" | "text">("pdf")
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cancelRef = useRef(false)

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    supabase.from("subjects").select("id, name, code, level, board").order("name")
      .then(({ data }) => setSubjects(data || []))
  }, [])

  useEffect(() => {
    if (!selectedSubject) return
    supabase.from("topics").select("id, code, name, description").eq("subject_id", selectedSubject.id).order("code")
      .then(({ data }) => {
        if (data && data.length > 0) {
          setTopics(data.map(t => ({ ...t, keywords: [] })))
        }
      })
  }, [selectedSubject])

  const loadStatus = useCallback(async (subject: Subject) => {
    setLoadingStatus(true)
    try {
      const res = await fetch(`/api/admin/pipeline/status?subjectId=${subject.id}`)
      setPipelineStatus(await res.json())
    } catch { showToast("Failed to load status", "err") }
    finally { setLoadingStatus(false) }
  }, [])

  const scanR2 = async () => {
    if (!selectedSubject) return
    setLoadingR2(true)
    setR2Scan(null)
    try {
      const res = await fetch(`/api/admin/pipeline/r2-scan?subjectId=${selectedSubject.id}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || "R2 scan failed")
      setR2Scan(data)
    } catch (err) {
      showToast(err instanceof Error ? err.message : "R2 scan failed", "err")
    } finally { setLoadingR2(false) }
  }

  const runClassification = async () => {
    if (!selectedSubject || classify.running) return
    cancelRef.current = false
    setClassify({ running: true, cancelled: false, processed: 0, classified: 0, errors: 0, total: 0, startTime: Date.now(), done: false, lastError: "" })

    let offset = 0
    const LIMIT = 40
    let totalProcessed = 0
    let totalClassified = 0
    let totalErrors = 0
    let grandTotal = 0
    const startTime = Date.now()

    while (!cancelRef.current) {
      try {
        const res = await fetch("/api/admin/pipeline/classify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            subjectId: selectedSubject.id,
            topics: topics.length > 0 ? topics : undefined,
            offset,
            limit: LIMIT,
            reclassify,
          }),
        })

        const data = await res.json()
        if (!res.ok) throw new Error(data.error || "Classification error")

        totalProcessed += data.processed
        totalClassified += data.classified
        totalErrors += data.errors
        grandTotal = data.total
        offset = data.nextOffset

        setClassify(prev => ({
          ...prev,
          processed: totalProcessed,
          classified: totalClassified,
          errors: totalErrors,
          total: grandTotal,
          startTime: prev.startTime || startTime,
        }))

        if (data.done || cancelRef.current) break

      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error"
        setClassify(prev => ({ ...prev, lastError: msg }))
        break
      }
    }

    setClassify(prev => ({
      ...prev,
      running: false,
      cancelled: cancelRef.current,
      done: !cancelRef.current,
    }))

    // Refresh status after classification
    await loadStatus(selectedSubject)
    showToast(cancelRef.current ? "Classification cancelled" : `Done — ${totalClassified} pages classified`)
  }

  const cancelClassification = () => {
    cancelRef.current = true
    setClassify(prev => ({ ...prev, cancelled: true }))
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.name.toLowerCase().endsWith(".pdf")) {
      const reader = new FileReader()
      reader.onload = evt => {
        const dataUrl = evt.target?.result as string
        setSpecPdfBase64(dataUrl.split(",")[1] ?? "")
        setSpecPdfName(file.name)
        setSpecText("")
      }
      reader.readAsDataURL(file)
    } else {
      const reader = new FileReader()
      reader.onload = evt => {
        setSpecText(evt.target?.result as string ?? "")
        setSpecPdfBase64("")
        setSpecPdfName("")
      }
      reader.readAsText(file)
    }
  }

  const analyzeSpec = async () => {
    const hasPdf = !!specPdfBase64
    const hasText = !!specText.trim()
    if ((!hasPdf && !hasText) || !selectedSubject) return
    setAnalyzing(true)
    try {
      const payload: Record<string, string> = {
        subjectName: selectedSubject.name,
        level: selectedSubject.level,
      }
      if (hasPdf) {
        payload.specPdfBase64 = specPdfBase64
      } else {
        payload.specText = specText
      }
      const res = await fetch("/api/admin/pipeline/analyze-spec", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || "Unknown error")
      setTopics(data.topics || [])
      showToast(`Generated ${data.topics?.length || 0} topics from specification`)
      setStep("topics")
    } catch (err) {
      showToast(`Analysis failed: ${err instanceof Error ? err.message : "Unknown error"}`, "err")
    } finally { setAnalyzing(false) }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const updateTopic = (idx: number, field: keyof Topic, value: any) =>
    setTopics(prev => prev.map((t, i) => i === idx ? { ...t, [field]: value } : t))

  const addTopic = () => {
    const nextId = String(topics.length + 1)
    setTopics(prev => [...prev, { id: nextId, code: `T${nextId}`, name: "New Topic", description: "", keywords: [] }])
  }

  const removeTopic = (idx: number) =>
    setTopics(prev => prev.filter((_, i) => i !== idx).map((t, i) => ({ ...t, id: String(i + 1) })))

  const saveTopics = async () => {
    if (!selectedSubject || topics.length === 0) return
    setSavingTopics(true)
    try {
      await supabase.from("topics").delete().eq("subject_id", selectedSubject.id)
      const { error } = await supabase.from("topics").insert(
        topics.map((t, i) => ({
          subject_id: selectedSubject.id,
          code: t.code || String(i + 1),
          name: t.name,
          description: t.description || "",
        }))
      )
      if (error) throw error
      showToast("Topics saved to database")
      setStep("status")
      loadStatus(selectedSubject)
    } catch (err) {
      showToast(`Save failed: ${err instanceof Error ? err.message : "Unknown error"}`, "err")
    } finally { setSavingTopics(false) }
  }

  const goToStatus = () => {
    if (!selectedSubject) return
    setStep("status")
    loadStatus(selectedSubject)
  }

  // ── Classify progress stats ──────────────────────────────────────────────
  const classifyElapsed = classify.startTime ? Date.now() - classify.startTime : 0
  const classifyRate = classify.processed > 0 ? classify.processed / classifyElapsed : 0
  const classifyEta = classifyRate > 0 ? (classify.total - classify.processed) / classifyRate : 0

  const cardStyle = { background: "var(--gm-surface)", borderRadius: "0.75rem", padding: "1.25rem", border: "1px solid var(--gm-border)" }

  return (
    <div style={{ padding: "2rem", maxWidth: 960, margin: "0 auto" }}>
      {toast && (
        <div style={{
          position: "fixed", top: 20, right: 20, zIndex: 999,
          padding: "0.75rem 1.25rem", borderRadius: "0.5rem",
          background: toast.type === "ok" ? "var(--gm-green)" : "#ef4444",
          color: "#fff", fontSize: "0.85rem", fontWeight: 600,
          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
        }}>
          {toast.msg}
        </div>
      )}

      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>
          Subject Pipeline
        </h1>
        <p style={{ color: "var(--gm-text-2)", fontSize: "0.85rem" }}>
          Upload a subject specification → AI generates topic guardrails → classify questions from R2 papers.
        </p>
      </div>

      {/* Step progress bar */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "2rem" }}>
        {STEPS.map(s => {
          const idx = STEPS.indexOf(step); const sIdx = STEPS.indexOf(s)
          const isActive = s === step; const isDone = sIdx < idx
          return (
            <div key={s} style={{ flex: 1 }}>
              <div style={{ height: 3, borderRadius: 2, background: isDone || isActive ? "var(--gm-blue)" : "var(--gm-border)", marginBottom: "0.4rem", transition: "background 0.2s" }} />
              <span style={{ fontSize: "0.7rem", fontWeight: isActive ? 700 : 400, color: isActive ? "var(--gm-blue)" : isDone ? "var(--gm-text-2)" : "var(--gm-text-3)" }}>
                {STEP_LABELS[s]}
              </span>
            </div>
          )
        })}
      </div>

      {/* ── STEP 1: Select Subject ────────────────────────────────────────── */}
      {step === "subject" && (
        <div style={cardStyle}>
          <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1rem", color: "var(--gm-text)" }}>Select a Subject</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "0.75rem" }}>
            {subjects.map(sub => (
              <button key={sub.id} onClick={() => setSelectedSubject(sub)} style={{
                padding: "0.75rem 1rem", borderRadius: "0.5rem", textAlign: "left",
                border: selectedSubject?.id === sub.id ? "2px solid var(--gm-blue)" : "1px solid var(--gm-border)",
                background: selectedSubject?.id === sub.id ? "rgba(110,168,254,0.1)" : "var(--gm-surface-2)",
                cursor: "pointer", transition: "all 0.15s",
              }}>
                <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--gm-text)" }}>{sub.name}</div>
                <div style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>{sub.code} · {sub.level?.toUpperCase()}</div>
              </button>
            ))}
          </div>
          <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem" }}>
            <Btn onClick={() => selectedSubject && setStep("spec")} disabled={!selectedSubject} primary>Next: Upload Spec</Btn>
            <Btn onClick={goToStatus} disabled={!selectedSubject}>Skip to Status</Btn>
          </div>
        </div>
      )}

      {/* ── STEP 2: Upload Specification ─────────────────────────────────── */}
      {step === "spec" && (
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--gm-text)" }}>
              Upload Specification — {selectedSubject?.name}
            </h2>
            <button onClick={() => setStep("subject")} style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", background: "none", border: "none", cursor: "pointer" }}>
              change
            </button>
          </div>

          <div style={{ background: "rgba(110,168,254,0.08)", border: "1px solid rgba(110,168,254,0.25)", borderRadius: "0.5rem", padding: "0.625rem 0.875rem", marginBottom: "1.25rem", fontSize: "0.8rem", color: "var(--gm-text-2)" }}>
            The specification is the <strong>sole source of truth</strong> for topic guardrails.
            Groq reads it and extracts include/exclude rules used during classification.
          </div>

          {/* Input mode tabs */}
          <div style={{ display: "flex", marginBottom: "1.25rem", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", overflow: "hidden" }}>
            {(["pdf", "text"] as const).map(m => (
              <button
                key={m}
                onClick={() => setSpecInputMode(m)}
                style={{
                  flex: 1, padding: "0.55rem 0", fontSize: "0.82rem", fontWeight: 600,
                  cursor: "pointer", border: "none",
                  background: specInputMode === m ? "var(--gm-blue)" : "var(--gm-surface-2)",
                  color: specInputMode === m ? "#fff" : "var(--gm-text-3)",
                  transition: "all 0.15s",
                }}
              >
                {m === "pdf" ? "📄 Upload PDF" : "📝 Paste Text"}
              </button>
            ))}
          </div>

          {/* PDF upload */}
          {specInputMode === "pdf" && (
            <>
              <div
                style={{ border: "2px dashed var(--gm-border-2)", borderRadius: "0.5rem", padding: "2.5rem 2rem", textAlign: "center", cursor: "pointer", transition: "border-color 0.15s", marginBottom: "0.75rem" }}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => {
                  e.preventDefault()
                  const file = e.dataTransfer.files?.[0]
                  if (file) handleFileUpload({ target: { files: [file] } } as unknown as React.ChangeEvent<HTMLInputElement>)
                }}
              >
                <div style={{ fontSize: "2.5rem", marginBottom: "0.625rem" }}>{specPdfName ? "📕" : "📄"}</div>
                {specPdfName ? (
                  <>
                    <p style={{ color: "var(--gm-green)", fontSize: "0.88rem", fontWeight: 700 }}>{specPdfName}</p>
                    <p style={{ color: "var(--gm-text-3)", fontSize: "0.75rem", marginTop: "0.25rem" }}>Click or drag to replace</p>
                  </>
                ) : (
                  <>
                    <p style={{ color: "var(--gm-text-2)", fontSize: "0.875rem", fontWeight: 600 }}>Click or drag &amp; drop the specification PDF</p>
                    <p style={{ color: "var(--gm-text-3)", fontSize: "0.75rem", marginTop: "0.25rem" }}>Text will be extracted and sent to Groq</p>
                  </>
                )}
              </div>
              <input ref={fileInputRef} type="file" accept=".pdf" style={{ display: "none" }} onChange={handleFileUpload} />
              {specPdfBase64 && (
                <p style={{ fontSize: "0.75rem", color: "var(--gm-green)", marginBottom: "0.5rem" }}>
                  ✓ PDF ready — Groq will extract topics from its text content
                </p>
              )}
            </>
          )}

          {/* Text paste */}
          {specInputMode === "text" && (
            <>
              <textarea
                value={specText}
                onChange={e => setSpecText(e.target.value)}
                placeholder="Paste the subject specification text here — topic names, learning objectives, assessment criteria..."
                style={{
                  width: "100%", minHeight: 240, padding: "0.75rem",
                  background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-input)",
                  borderRadius: "0.5rem", color: "var(--gm-text)", fontSize: "0.82rem",
                  resize: "vertical", outline: "none", boxSizing: "border-box", fontFamily: "monospace",
                }}
              />
              <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.4rem", marginBottom: "0.25rem" }}>
                {specText.length.toLocaleString()} characters
              </p>
            </>
          )}

          <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
            <button
              onClick={analyzeSpec}
              disabled={(!specText.trim() && !specPdfBase64) || analyzing}
              style={{
                padding: "0.6rem 1.25rem", borderRadius: "0.5rem", fontSize: "0.85rem",
                fontWeight: 600, cursor: (!specText.trim() && !specPdfBase64) || analyzing ? "not-allowed" : "pointer",
                background: (!specText.trim() && !specPdfBase64) || analyzing ? "var(--gm-border)" : "var(--gm-amber)",
                color: (!specText.trim() && !specPdfBase64) || analyzing ? "var(--gm-text-3)" : "#000", border: "none",
                display: "flex", alignItems: "center", gap: "0.5rem",
              }}
            >
              {analyzing
                ? <><span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span> Analyzing with Groq…</>
                : "Analyze with Groq"}
            </button>
            <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)" }}>llama-3.3-70b-versatile · 6–12 topics with guardrails</span>
            <Btn onClick={() => { setTopics([]); setStep("topics") }}>Skip (manual)</Btn>
          </div>
        </div>
      )}

      {/* ── STEP 3: Review & Edit Topics ─────────────────────────────────── */}
      {step === "topics" && (
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
            <div>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--gm-text)" }}>Review Topics — {selectedSubject?.name}</h2>
              <p style={{ color: "var(--gm-text-3)", fontSize: "0.75rem", marginTop: "0.2rem" }}>
                Guardrails here (include/exclude rules) drive classification accuracy — edit before saving.
              </p>
            </div>
            <button onClick={addTopic} style={{ padding: "0.4rem 0.8rem", borderRadius: "0.375rem", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer", background: "var(--gm-surface-3)", border: "1px solid var(--gm-border)", color: "var(--gm-text)" }}>
              + Add Topic
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {topics.map((t, idx) => (
              <div key={idx} style={{ background: "var(--gm-surface-2)", borderRadius: "0.5rem", padding: "1rem", border: editingTopicIdx === idx ? "1px solid var(--gm-blue)" : "1px solid var(--gm-border)" }}>
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                  <div style={{ minWidth: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--gm-blue)", color: "#fff", fontSize: "0.7rem", fontWeight: 700, flexShrink: 0 }}>
                    {t.id}
                  </div>
                  {editingTopicIdx === idx ? (
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <InlineInput value={t.code} onChange={v => updateTopic(idx, "code", v.toUpperCase())} placeholder="CODE" style={{ width: 80, fontWeight: 700 }} />
                        <InlineInput value={t.name} onChange={v => updateTopic(idx, "name", v)} placeholder="Topic Name" style={{ flex: 1 }} />
                      </div>
                      <InlineTextarea value={t.description} onChange={v => updateTopic(idx, "description", v)} placeholder="Description" rows={2} />
                      <InlineTextarea
                        value={t.guardrails?.include_when || ""}
                        onChange={v => updateTopic(idx, "guardrails", { ...t.guardrails, include_when: v })}
                        placeholder="Classify AS this topic when... (from specification)"
                        rows={2}
                        style={{ borderColor: "rgba(52,211,153,0.4)" }}
                      />
                      <InlineTextarea
                        value={t.guardrails?.exclude_when || ""}
                        onChange={v => updateTopic(idx, "guardrails", { ...t.guardrails, exclude_when: v })}
                        placeholder="Do NOT classify as this topic when... (from specification)"
                        rows={2}
                        style={{ borderColor: "rgba(239,68,68,0.4)" }}
                      />
                      <InlineInput
                        value={(t.keywords || []).join(", ")}
                        onChange={v => updateTopic(idx, "keywords", v.split(",").map(k => k.trim()).filter(Boolean))}
                        placeholder="keywords, comma, separated"
                      />
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button onClick={() => setEditingTopicIdx(null)} style={{ padding: "0.3rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.75rem", background: "var(--gm-green)", color: "#000", border: "none", cursor: "pointer", fontWeight: 600 }}>Done</button>
                        <button onClick={() => removeTopic(idx)} style={{ padding: "0.3rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.75rem", background: "#ef444420", color: "#ef4444", border: "1px solid #ef444430", cursor: "pointer" }}>Remove</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
                        <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--gm-blue)", background: "rgba(110,168,254,0.12)", padding: "0.1rem 0.4rem", borderRadius: "0.25rem" }}>{t.code}</span>
                        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--gm-text)" }}>{t.name}</span>
                        {t.guardrails?.include_when && <span style={{ fontSize: "0.6rem", color: "var(--gm-green)", background: "rgba(52,211,153,0.1)", padding: "0.1rem 0.3rem", borderRadius: "0.25rem" }}>guardrails</span>}
                      </div>
                      <p style={{ fontSize: "0.75rem", color: "var(--gm-text-2)", margin: 0 }}>{t.description}</p>
                      {t.keywords && t.keywords.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginTop: "0.4rem" }}>
                          {t.keywords.slice(0, 6).map(k => <span key={k} style={{ fontSize: "0.65rem", padding: "0.1rem 0.35rem", borderRadius: "0.25rem", background: "var(--gm-surface-3)", color: "var(--gm-text-3)" }}>{k}</span>)}
                          {t.keywords.length > 6 && <span style={{ fontSize: "0.65rem", color: "var(--gm-text-3)" }}>+{t.keywords.length - 6}</span>}
                        </div>
                      )}
                    </div>
                  )}
                  {editingTopicIdx !== idx && (
                    <button onClick={() => setEditingTopicIdx(idx)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--gm-text-3)", fontSize: "0.8rem", padding: "0.25rem" }}>✎</button>
                  )}
                </div>
              </div>
            ))}
            {topics.length === 0 && (
              <div style={{ textAlign: "center", padding: "2rem", color: "var(--gm-text-3)", fontSize: "0.85rem" }}>
                No topics yet. Analyze a specification or add topics manually.
              </div>
            )}
          </div>

          <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem" }}>
            <Btn onClick={saveTopics} disabled={topics.length === 0 || savingTopics} primary>
              {savingTopics ? "Saving..." : `Save ${topics.length} Topics to DB`}
            </Btn>
            <Btn onClick={() => setStep("spec")}>Back</Btn>
            <Btn onClick={goToStatus}>View Status</Btn>
          </div>
        </div>
      )}

      {/* ── STEP 4: Pipeline Status ───────────────────────────────────────── */}
      {step === "status" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

          {/* Header row */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--gm-text)" }}>Pipeline Status — {selectedSubject?.name}</h2>
              <p style={{ color: "var(--gm-text-3)", fontSize: "0.75rem" }}>{selectedSubject?.code} · {selectedSubject?.level?.toUpperCase()}</p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <Btn onClick={() => selectedSubject && loadStatus(selectedSubject)} disabled={loadingStatus} small>
                {loadingStatus ? "Refreshing..." : "Refresh"}
              </Btn>
              <Btn onClick={() => setStep("subject")} small>Change Subject</Btn>
            </div>
          </div>

          {loadingStatus && <div style={{ textAlign: "center", padding: "3rem", color: "var(--gm-text-3)" }}>Loading status...</div>}

          {pipelineStatus && !loadingStatus && (
            <>
              {/* Stage cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
                {[
                  { stage: "Stage 1", label: "Papers in DB", value: pipelineStatus.papers, total: pipelineStatus.papers, icon: "📂", color: "var(--gm-blue)" },
                  { stage: "Stage 2", label: "Pages Created", value: pipelineStatus.pages, total: pipelineStatus.pages, icon: "📄", color: "var(--gm-blue)" },
                  { stage: "Stage 3", label: "URLs Uploaded", value: pipelineStatus.pagesWithUrl, total: pipelineStatus.pages, icon: "☁️", color: "var(--gm-amber)" },
                  { stage: "Stage 4", label: "Classified", value: pipelineStatus.pagesClassified, total: pipelineStatus.pages, icon: "🏷️", color: "var(--gm-green)" },
                ].map(card => {
                  const p = pct(card.value, card.total)
                  const isComplete = card.total > 0 && p === 100
                  return (
                    <div key={card.label} style={{ background: "var(--gm-surface)", borderRadius: "0.75rem", padding: "1rem", border: `1px solid ${isComplete ? "rgba(52,211,153,0.3)" : "var(--gm-border)"}` }}>
                      <div style={{ fontSize: "1.25rem", marginBottom: "0.4rem" }}>{card.icon}</div>
                      <div style={{ fontSize: "1.3rem", fontWeight: 800, color: card.color }}>{card.value.toLocaleString()}</div>
                      <div style={{ fontSize: "0.6rem", fontWeight: 600, color: "var(--gm-text-3)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{card.stage}</div>
                      <div style={{ fontSize: "0.7rem", color: "var(--gm-text-2)", marginBottom: "0.5rem" }}>{card.label}</div>
                      {card.total > 0 && (
                        <>
                          <div style={{ height: 4, background: "var(--gm-surface-3)", borderRadius: 2 }}>
                            <div style={{ height: "100%", borderRadius: 2, background: isComplete ? "var(--gm-green)" : card.color, width: `${p}%`, transition: "width 0.4s ease" }} />
                          </div>
                          <div style={{ fontSize: "0.65rem", color: isComplete ? "var(--gm-green)" : "var(--gm-text-3)", marginTop: "0.3rem" }}>{p}% {isComplete ? "✓" : ""}</div>
                        </>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* ── R2 Paper Coverage ── */}
              <div style={cardStyle}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <div>
                    <h3 style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gm-text)" }}>R2 Paper Coverage</h3>
                    <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>
                      Papers found in Cloudflare R2 vs papers ingested into the database
                    </p>
                  </div>
                  <button
                    onClick={scanR2}
                    disabled={loadingR2}
                    style={{
                      padding: "0.4rem 0.9rem", borderRadius: "0.375rem", fontSize: "0.75rem",
                      fontWeight: 600, cursor: loadingR2 ? "not-allowed" : "pointer",
                      background: loadingR2 ? "var(--gm-border)" : "rgba(110,168,254,0.15)",
                      border: "1px solid rgba(110,168,254,0.3)", color: loadingR2 ? "var(--gm-text-3)" : "var(--gm-blue)",
                    }}
                  >
                    {loadingR2 ? "Scanning R2..." : r2Scan ? "Re-scan R2" : "Scan R2"}
                  </button>
                </div>

                {r2Scan && (
                  <>
                    {/* Summary chips */}
                    <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
                      {[
                        { label: `${r2Scan.r2Count} in R2`, color: "var(--gm-blue)", bg: "rgba(110,168,254,0.1)" },
                        { label: `${r2Scan.stats.inBoth} in DB`, color: "var(--gm-green)", bg: "rgba(52,211,153,0.1)" },
                        { label: `${r2Scan.stats.r2Only} missing from DB`, color: "var(--gm-amber)", bg: "rgba(251,191,36,0.1)" },
                        ...(r2Scan.stats.dbOnly > 0 ? [{ label: `${r2Scan.stats.dbOnly} orphaned in DB`, color: "#ef4444", bg: "rgba(239,68,68,0.1)" }] : []),
                      ].map(chip => (
                        <span key={chip.label} style={{ fontSize: "0.72rem", fontWeight: 600, padding: "0.2rem 0.6rem", borderRadius: "1rem", color: chip.color, background: chip.bg }}>
                          {chip.label}
                        </span>
                      ))}
                      <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", padding: "0.2rem 0.4rem" }}>
                        R2 folder: <code style={{ fontFamily: "monospace" }}>{r2Scan.subjectFolder}/</code>
                      </span>
                    </div>

                    {/* Paper table */}
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
                        <thead>
                          <tr style={{ borderBottom: "1px solid var(--gm-border)" }}>
                            {["Year", "Session", "Paper", "QP in R2", "MS in R2", "In DB", "Status"].map(h => (
                              <th key={h} style={{ padding: "0.4rem 0.5rem", textAlign: "left", color: "var(--gm-text-3)", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {r2Scan.comparison.map(row => (
                            <tr key={row.groupKey} style={{ borderBottom: "1px solid var(--gm-border)", background: !row.inDb ? "rgba(251,191,36,0.04)" : "transparent" }}>
                              <td style={{ padding: "0.4rem 0.5rem", color: "var(--gm-text)" }}>{row.year}</td>
                              <td style={{ padding: "0.4rem 0.5rem", color: "var(--gm-text-2)" }}>{row.session}</td>
                              <td style={{ padding: "0.4rem 0.5rem", color: "var(--gm-text)" }}>{row.paperNumber}</td>
                              <td style={{ padding: "0.4rem 0.5rem" }}><StatusDot ok={!!row.r2QP} /></td>
                              <td style={{ padding: "0.4rem 0.5rem" }}><StatusDot ok={!!row.r2MS} /></td>
                              <td style={{ padding: "0.4rem 0.5rem" }}><StatusDot ok={row.inDb} /></td>
                              <td style={{ padding: "0.4rem 0.5rem" }}>
                                {!row.inDb ? (
                                  <span style={{ fontSize: "0.65rem", color: "var(--gm-amber)", fontWeight: 600 }}>Needs segmentation</span>
                                ) : (
                                  <span style={{ fontSize: "0.65rem", color: "var(--gm-green)" }}>In pipeline</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {r2Scan.stats.r2Only > 0 && (
                      <div style={{ marginTop: "0.75rem", padding: "0.65rem 0.85rem", background: "rgba(251,191,36,0.08)", borderRadius: "0.375rem", border: "1px solid rgba(251,191,36,0.2)", fontSize: "0.75rem", color: "var(--gm-text-2)" }}>
                        <strong style={{ color: "var(--gm-amber)" }}>{r2Scan.stats.r2Only} paper{r2Scan.stats.r2Only > 1 ? "s" : ""}</strong> found in R2 but not yet segmented/ingested.
                        Run <code style={{ fontFamily: "monospace", fontSize: "0.72rem", background: "var(--gm-bg)", padding: "0 0.3rem", borderRadius: "0.2rem" }}>python scripts/segment_maths_b_papers.py</code> then the ingest script for the subject.
                      </div>
                    )}
                  </>
                )}

                {!r2Scan && !loadingR2 && (
                  <div style={{ textAlign: "center", padding: "1.5rem", color: "var(--gm-text-3)", fontSize: "0.8rem" }}>
                    Click &ldquo;Scan R2&rdquo; to check which papers exist in Cloudflare R2 and compare with the database.
                  </div>
                )}
              </div>

              {/* ── Classification Runner ── */}
              <div style={cardStyle}>
                <h3 style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.5rem" }}>Classification</h3>
                <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "1rem" }}>
                  Uses Groq (llama-3.1-8b-instant) with spec-derived topic guardrails.
                  {topics.length > 0
                    ? <> <strong style={{ color: "var(--gm-green)" }}>{topics.length} topics with {topics.filter(t => t.guardrails?.include_when).length} guardrails</strong> loaded from this session.</>
                    : <> <span style={{ color: "var(--gm-amber)" }}>No spec-derived guardrails in session</span> — go back to analyze spec for best results.</>}
                </p>

                {/* Progress display */}
                {(classify.running || classify.done || classify.processed > 0) && (
                  <div style={{ marginBottom: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
                      <span style={{ fontSize: "0.8rem", color: "var(--gm-text)", fontWeight: 600 }}>
                        {classify.processed.toLocaleString()} / {classify.total.toLocaleString()} pages
                        {classify.classified > 0 && <span style={{ color: "var(--gm-green)", marginLeft: "0.4rem" }}>({classify.classified} classified)</span>}
                        {classify.errors > 0 && <span style={{ color: "#ef4444", marginLeft: "0.4rem" }}>({classify.errors} errors)</span>}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>
                        {classify.running && classifyEta > 0 ? fmtEta(classifyEta) + " remaining" : ""}
                        {classify.done && !classify.cancelled ? "Complete" : ""}
                        {classify.cancelled ? "Cancelled" : ""}
                      </span>
                    </div>
                    {/* Progress bar */}
                    <div style={{ height: 8, background: "var(--gm-surface-3)", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{
                        height: "100%",
                        width: `${pct(classify.processed, classify.total)}%`,
                        background: classify.done && !classify.cancelled ? "var(--gm-green)" : classify.cancelled ? "#ef4444" : "var(--gm-blue)",
                        borderRadius: 4,
                        transition: "width 0.5s ease",
                        backgroundImage: classify.running ? "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%)" : "none",
                        backgroundSize: "200% 100%",
                        animation: classify.running ? "shimmer 1.5s infinite" : "none",
                      }} />
                    </div>
                    <div style={{ marginTop: "0.3rem", fontSize: "0.7rem", color: "var(--gm-text-3)" }}>
                      {pct(classify.processed, classify.total)}%
                      {classify.running && classifyElapsed > 2000 && ` · ${Math.round(classifyElapsed / 1000)}s elapsed`}
                    </div>
                    {classify.lastError && (
                      <div style={{ marginTop: "0.4rem", fontSize: "0.72rem", color: "#ef4444", background: "rgba(239,68,68,0.08)", padding: "0.3rem 0.5rem", borderRadius: "0.25rem" }}>
                        {classify.lastError}
                      </div>
                    )}
                  </div>
                )}

                <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                  {!classify.running ? (
                    <>
                      <button
                        onClick={runClassification}
                        disabled={pipelineStatus.pagesWithUrl === 0}
                        style={{
                          padding: "0.6rem 1.25rem", borderRadius: "0.5rem", fontSize: "0.85rem",
                          fontWeight: 600, cursor: pipelineStatus.pagesWithUrl === 0 ? "not-allowed" : "pointer",
                          background: pipelineStatus.pagesWithUrl === 0 ? "var(--gm-border)" : "var(--gm-blue)",
                          color: pipelineStatus.pagesWithUrl === 0 ? "var(--gm-text-3)" : "#fff", border: "none",
                        }}
                      >
                        {classify.done ? "Re-run Classification" : "Run Classification"}
                      </button>
                      <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.78rem", color: "var(--gm-text-2)", cursor: "pointer" }}>
                        <input type="checkbox" checked={reclassify} onChange={e => setReclassify(e.target.checked)} />
                        Re-classify already tagged pages
                      </label>
                      {pipelineStatus.pagesWithUrl === 0 && (
                        <span style={{ fontSize: "0.75rem", color: "var(--gm-amber)" }}>
                          No pages with URLs found — run the ingest script first.
                        </span>
                      )}
                    </>
                  ) : (
                    <button
                      onClick={cancelClassification}
                      style={{
                        padding: "0.6rem 1.25rem", borderRadius: "0.5rem", fontSize: "0.85rem",
                        fontWeight: 600, cursor: "pointer",
                        background: "#ef444420", border: "1px solid #ef444440", color: "#ef4444",
                      }}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>

              {/* Topic distribution */}
              {Object.keys(pipelineStatus.topicDistribution).length > 0 && (
                <div style={cardStyle}>
                  <h3 style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.75rem" }}>Topic Distribution</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                    {Object.entries(pipelineStatus.topicDistribution)
                      .sort((a, b) => b[1] - a[1])
                      .map(([topicId, count]) => {
                        const total = Object.values(pipelineStatus.topicDistribution).reduce((a, b) => a + b, 0)
                        const p = pct(count, total)
                        const topicObj = topics.find(t => t.id === topicId || t.code === topicId)
                        return (
                          <div key={topicId} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", minWidth: 60, textAlign: "right" }}>
                              {topicObj?.name || topicObj?.code || topicId}
                            </span>
                            <div style={{ flex: 1, height: 6, background: "var(--gm-surface-3)", borderRadius: 3 }}>
                              <div style={{ height: "100%", borderRadius: 3, background: "var(--gm-blue)", width: `${p}%` }} />
                            </div>
                            <span style={{ fontSize: "0.7rem", color: "var(--gm-text-2)", minWidth: 55, textAlign: "right" }}>{count} ({p}%)</span>
                          </div>
                        )
                      })}
                  </div>
                </div>
              )}

              {/* Difficulty distribution */}
              {Object.keys(pipelineStatus.difficultyDistribution).length > 0 && (
                <div style={cardStyle}>
                  <h3 style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.75rem" }}>Difficulty Distribution</h3>
                  <div style={{ display: "flex", gap: "1rem" }}>
                    {["easy", "medium", "hard"].map(d => {
                      const count = pipelineStatus.difficultyDistribution[d] || 0
                      const total = Object.values(pipelineStatus.difficultyDistribution).reduce((a, b) => a + b, 0)
                      const p = pct(count, total)
                      const colors: Record<string, string> = { easy: "var(--gm-green)", medium: "var(--gm-amber)", hard: "#ef4444" }
                      return (
                        <div key={d} style={{ flex: 1, textAlign: "center", padding: "0.75rem", background: "var(--gm-surface-2)", borderRadius: "0.5rem" }}>
                          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: colors[d] }}>{p}%</div>
                          <div style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", textTransform: "capitalize", marginTop: "0.2rem" }}>{d}</div>
                          <div style={{ fontSize: "0.65rem", color: "var(--gm-text-3)" }}>{count} pages</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
      `}</style>
    </div>
  )
}

// ── Small reusable components ────────────────────────────────────────────────

function Btn({ onClick, disabled, primary, small, children }: {
  onClick: () => void; disabled?: boolean; primary?: boolean; small?: boolean; children: React.ReactNode
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: small ? "0.35rem 0.75rem" : "0.6rem 1.25rem",
      borderRadius: "0.5rem", fontSize: small ? "0.75rem" : "0.85rem",
      fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer",
      background: disabled ? "var(--gm-border)" : primary ? "var(--gm-blue)" : "transparent",
      color: disabled ? "var(--gm-text-3)" : primary ? "#fff" : "var(--gm-text)",
      border: primary || disabled ? "none" : "1px solid var(--gm-border)",
      transition: "all 0.15s",
    }}>
      {children}
    </button>
  )
}

function InlineInput({ value, onChange, placeholder, style }: {
  value: string; onChange: (v: string) => void; placeholder?: string; style?: React.CSSProperties
}) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        padding: "0.35rem 0.5rem", borderRadius: "0.375rem",
        background: "var(--gm-surface)", border: "1px solid var(--gm-border-input)",
        color: "var(--gm-text)", fontSize: "0.8rem", outline: "none",
        boxSizing: "border-box" as const, ...style,
      }}
    />
  )
}

function InlineTextarea({ value, onChange, placeholder, rows, style }: {
  value: string; onChange: (v: string) => void; placeholder?: string; rows?: number; style?: React.CSSProperties
}) {
  return (
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows || 2}
      style={{
        width: "100%", padding: "0.35rem 0.5rem", borderRadius: "0.375rem",
        background: "var(--gm-surface)", border: "1px solid var(--gm-border-input)",
        color: "var(--gm-text)", fontSize: "0.78rem", outline: "none",
        resize: "vertical" as const, boxSizing: "border-box" as const, ...style,
      }}
    />
  )
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: ok ? "var(--gm-green)" : "var(--gm-border)",
    }} />
  )
}
