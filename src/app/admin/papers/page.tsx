"use client"
import { useEffect, useState, useCallback, useRef, DragEvent } from "react"

interface Subject { id: string; name: string; code: string | null; level: string }
interface AuditRow {
  paperId: string | null
  year: number; season: string; paperNumber: string
  dbHasQP: boolean; dbHasMS: boolean; r2HasQP: boolean; r2HasMS: boolean
  r2QpKey: string | null; r2MsKey: string | null
}
interface QueueItem {
  id: string
  file: File
  year: string
  session: string
  paper: string
  type: "QP" | "MS"
  status: "pending" | "uploading" | "done" | "error"
  message?: string
  r2Key?: string
}

const Dot = ({ ok }: { ok: boolean }) => (
  <span style={{
    display: "inline-block", width: "0.625rem", height: "0.625rem",
    borderRadius: "50%", background: ok ? "#22c55e" : "#ef444440",
    border: ok ? "none" : "1px solid #ef444460",
  }} />
)

const SEASONS = ["Jan", "May-Jun", "Oct-Nov", "Specimen"] as const

function parseFilenameFields(name: string): Partial<Pick<QueueItem, "year" | "session" | "paper" | "type">> {
  const m = name.match(/(\d{4})_(Jan|May-Jun|Oct-Nov|Specimen)_Paper_([\w]+)_(QP|MS)\.pdf$/i)
  if (!m) return {}
  return {
    year: m[1],
    session: m[2].split("-").map((p: string) => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()).join("-"),
    paper: m[3].toUpperCase(),
    type: m[4].toUpperCase() as "QP" | "MS",
  }
}

export default function PapersAdminPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedId, setSelectedId] = useState("")
  const [auditRows, setAuditRows] = useState<AuditRow[]>([])
  const [auditLoading, setAuditLoading] = useState(false)
  const [subjectName, setSubjectName] = useState("")

  // Upload queue
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [uploadingAll, setUploadingAll] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null)

  // Single-file form state (for quick single upload)
  const [file, setFile] = useState<File | null>(null)
  const [uploadType, setUploadType] = useState<"QP" | "MS">("QP")
  const [uploadYear, setUploadYear] = useState("")
  const [uploadSession, setUploadSession] = useState("")
  const [uploadPaper, setUploadPaper] = useState("")
  const [uploading, setUploading] = useState(false)
  const [overwriteWarning, setOverwriteWarning] = useState<string | null>(null)
  const [pendingSubmit, setPendingSubmit] = useState(false)

  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"upload" | "queue" | "audit">("upload")
  const [exportingReport, setExportingReport] = useState(false)

  // Audit filters
  const [filterStatus, setFilterStatus] = useState<"all" | "incomplete" | "missing_both" | "missing_qp" | "missing_ms">("all")
  const [filterYear, setFilterYear] = useState<string>("all")

  // Delete state
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null)

  // Validation errors
  const [formErrors, setFormErrors] = useState<Partial<Record<"year" | "session" | "paper", string>>>({})

  const dropRef = useRef<HTMLDivElement>(null)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    fetch("/api/admin/subjects").then(r => r.json()).then(d => setSubjects(d.subjects || []))
  }, [])

  const runAudit = useCallback(async (id: string) => {
    if (!id) return
    setAuditLoading(true)
    setAuditRows([])
    const res = await fetch(`/api/admin/papers/audit?subject_id=${id}`)
    const data = await res.json()
    setAuditRows(data.rows || [])
    setSubjectName(data.subject || "")
    setAuditLoading(false)
  }, [])

  const handleSubjectChange = (id: string) => {
    setSelectedId(id)
    setAuditRows([])
    setSyncMsg(null)
    setUploadMsg(null)
    setFormErrors({})
    setOverwriteWarning(null)
    setFilterStatus("all")
    setFilterYear("all")
  }

  const handleFileChange = (f: File | null) => {
    setFile(f)
    setUploadMsg(null)
    setOverwriteWarning(null)
    if (!f) return
    const parsed = parseFilenameFields(f.name)
    if (parsed.year) setUploadYear(parsed.year)
    if (parsed.session) setUploadSession(parsed.session)
    if (parsed.paper) setUploadPaper(parsed.paper)
    if (parsed.type) setUploadType(parsed.type)
    if (Object.keys(parsed).length > 0) setFormErrors({})
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith(".pdf"))
    if (files.length === 0) return
    if (files.length === 1) {
      handleFileChange(files[0])
    } else {
      // Multi-file → add to queue
      const newItems: QueueItem[] = files.map(f => {
        const parsed = parseFilenameFields(f.name)
        return {
          id: `${Date.now()}-${Math.random()}`,
          file: f,
          year: parsed.year || "",
          session: parsed.session || "",
          paper: parsed.paper || "",
          type: parsed.type || "QP",
          status: "pending",
        }
      })
      setQueue(prev => [...prev, ...newItems])
      setActiveTab("queue")
    }
  }

  const handleFilesSelected = (files: FileList | null) => {
    if (!files) return
    const pdfs = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".pdf"))
    if (pdfs.length === 0) return
    if (pdfs.length === 1) {
      handleFileChange(pdfs[0])
    } else {
      const newItems: QueueItem[] = pdfs.map(f => {
        const parsed = parseFilenameFields(f.name)
        return {
          id: `${Date.now()}-${Math.random()}`,
          file: f,
          year: parsed.year || "",
          session: parsed.session || "",
          paper: parsed.paper || "",
          type: parsed.type || "QP",
          status: "pending",
        }
      })
      setQueue(prev => [...prev, ...newItems])
      setActiveTab("queue")
    }
  }

  const validateForm = (): boolean => {
    const errs: typeof formErrors = {}
    if (!uploadYear || !/^\d{4}$/.test(uploadYear)) errs.year = "Enter a valid 4-digit year"
    if (!uploadSession) errs.session = "Select a session"
    if (!uploadPaper) errs.paper = "Enter paper number (e.g. 1, 2, 1R)"
    setFormErrors(errs)
    return Object.keys(errs).length === 0
  }

  const checkOverwrite = (): boolean => {
    if (!auditRows.length) return false
    const season = uploadSession.toLowerCase()
    const existing = auditRows.find(r =>
      r.year === parseInt(uploadYear) &&
      r.season === season &&
      r.paperNumber === uploadPaper.toUpperCase()
    )
    if (!existing) return false
    if (uploadType === "QP" && existing.dbHasQP) return true
    if (uploadType === "MS" && existing.dbHasMS) return true
    return false
  }

  const doUpload = async () => {
    if (!file || !selectedId) return
    setUploading(true)
    setUploadMsg(null)
    setOverwriteWarning(null)
    const fd = new FormData()
    fd.append("file", file)
    fd.append("subject_id", selectedId)
    fd.append("year", uploadYear)
    fd.append("session", uploadSession)
    fd.append("paper_number", uploadPaper)
    fd.append("type", uploadType)

    const res = await fetch("/api/admin/papers/upload", { method: "POST", body: fd })
    const data = await res.json()

    if (res.ok) {
      setUploadMsg({ type: "ok", text: `✓ Uploaded → ${data.r2Key}` })
      setFile(null); setUploadYear(""); setUploadSession(""); setUploadPaper(""); setUploadType("QP"); setFormErrors({})
      const input = document.getElementById("pdf-input") as HTMLInputElement
      if (input) input.value = ""
      if (auditRows.length > 0) runAudit(selectedId)
    } else {
      setUploadMsg({ type: "err", text: data.error || "Upload failed" })
    }
    setUploading(false)
    setPendingSubmit(false)
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !selectedId) return
    if (!validateForm()) return

    if (checkOverwrite() && !pendingSubmit) {
      setOverwriteWarning(`A ${uploadType} for ${uploadYear} ${uploadSession} Paper ${uploadPaper} already exists in the database. Click Upload again to overwrite.`)
      setPendingSubmit(true)
      return
    }
    await doUpload()
  }

  const handleSync = async () => {
    if (!selectedId) return
    setSyncing(true)
    setSyncMsg(null)
    const res = await fetch("/api/admin/papers/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject_id: selectedId }),
    })
    const data = await res.json()
    if (res.ok) {
      setSyncMsg(`Scanned ${data.r2ObjectsScanned} R2 files — Inserted: ${data.inserted}, Updated: ${data.updated}${data.failedCount ? `, Failed: ${data.failedCount}` : ""}`)
      runAudit(selectedId)
    } else {
      setSyncMsg(`Error: ${data.error}`)
    }
    setSyncing(false)
  }

  // Upload all items in queue
  const handleUploadQueue = async () => {
    if (!selectedId || uploadingAll) return
    setUploadingAll(true)
    const pending = queue.filter(item => item.status === "pending" && item.year && item.session && item.paper)
    for (const item of pending) {
      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: "uploading" } : q))
      const fd = new FormData()
      fd.append("file", item.file)
      fd.append("subject_id", selectedId)
      fd.append("year", item.year)
      fd.append("session", item.session)
      fd.append("paper_number", item.paper)
      fd.append("type", item.type)
      try {
        const res = await fetch("/api/admin/papers/upload", { method: "POST", body: fd })
        const data = await res.json()
        if (res.ok) {
          setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: "done", r2Key: data.r2Key } : q))
        } else {
          setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: "error", message: data.error } : q))
        }
      } catch (err) {
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: "error", message: String(err) } : q))
      }
    }
    setUploadingAll(false)
    if (auditRows.length > 0) runAudit(selectedId)
  }

  // Add R2 file to DB row
  const handleAddToDB = async (row: AuditRow) => {
    if (!selectedId) return
    const res = await fetch("/api/admin/papers/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject_id: selectedId,
        year: row.year,
        season: row.season,
        paper_number: row.paperNumber,
      }),
    })
    const data = await res.json()
    if (res.ok) {
      runAudit(selectedId)
    } else {
      alert(data.error || "Sync failed")
    }
  }

  // Delete paper from DB (and optionally R2)
  const handleDeletePaper = async (row: AuditRow) => {
    if (!row.paperId) return
    const withR2 = window.confirm(
      `Delete DB record for ${row.year} ${row.season} Paper ${row.paperNumber}?\n\nClick OK to also delete R2 files, or Cancel to keep R2 files.`
    )
    // We confirmed — now delete
    if (!window.confirm(`Confirm: delete ${withR2 ? "DB + R2 files" : "DB record only"} for ${row.year} ${row.season} P${row.paperNumber}?`)) return
    setDeletingPaperId(row.paperId)
    const res = await fetch(`/api/admin/papers/${row.paperId}?deleteR2=${withR2}`, { method: "DELETE" })
    const data = await res.json()
    setDeletingPaperId(null)
    if (res.ok) {
      runAudit(selectedId)
    } else {
      alert(data.error || "Delete failed")
    }
  }

  const handleExportReport = async () => {
    setExportingReport(true)
    try {
      const res = await fetch("/api/admin/papers/full-audit")
      const data = await res.json()
      if (!res.ok) { alert(data.error || "Export failed"); return }

      const rows: string[] = ["Subject,Level,Year,Session,Paper,DB_QP,DB_MS,R2_QP,R2_MS,Status"]
      for (const row of data.rows) {
        const status = (row.dbHasQP && row.dbHasMS) ? "complete" : (!row.dbHasQP && !row.dbHasMS) ? "missing_both" : !row.dbHasQP ? "missing_qp" : "missing_ms"
        rows.push([row.subject, row.level, row.year, row.season, row.paperNumber,
          row.dbHasQP, row.dbHasMS, row.r2HasQP, row.r2HasMS, status].join(","))
      }

      const blob = new Blob([rows.join("\n")], { type: "text/csv" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a"); a.href = url
      a.download = `grademax-papers-audit-${new Date().toISOString().slice(0, 10)}.csv`
      a.click(); URL.revokeObjectURL(url)
    } catch { alert("Export failed") }
    setExportingReport(false)
  }

  const inputStyle: React.CSSProperties = {
    background: "var(--gm-bg)", border: "1px solid var(--gm-border)",
    borderRadius: "0.5rem", padding: "0.5rem 0.75rem",
    color: "var(--gm-text)", fontSize: "0.8rem", width: "100%", outline: "none",
  }
  const inputErrStyle: React.CSSProperties = { ...inputStyle, borderColor: "#ef4444" }
  const labelStyle: React.CSSProperties = { fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.25rem", display: "block" }
  const errMsgStyle: React.CSSProperties = { fontSize: "0.7rem", color: "#ef4444", marginTop: "0.2rem" }

  const missingCount = auditRows.filter(r => !r.dbHasQP || !r.dbHasMS || !r.r2HasQP || !r.r2HasMS).length

  // Filtered audit rows
  const allYears = Array.from(new Set(auditRows.map(r => r.year))).sort((a, b) => b - a)
  const filteredRows = auditRows.filter(r => {
    if (filterYear !== "all" && r.year !== parseInt(filterYear)) return false
    if (filterStatus === "all") return true
    if (filterStatus === "incomplete") return !r.dbHasQP || !r.dbHasMS
    if (filterStatus === "missing_both") return !r.dbHasQP && !r.dbHasMS
    if (filterStatus === "missing_qp") return !r.dbHasQP && r.dbHasMS
    if (filterStatus === "missing_ms") return r.dbHasQP && !r.dbHasMS
    return true
  })

  const queuePending = queue.filter(q => q.status === "pending").length
  const queueDone = queue.filter(q => q.status === "done").length
  const queueError = queue.filter(q => q.status === "error").length

  return (
    <div
      style={{ padding: "2rem", maxWidth: "1100px" }}
      ref={dropRef}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {dragOver && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 999, background: "var(--gm-blue)20",
          border: "3px dashed var(--gm-blue)", display: "flex", alignItems: "center",
          justifyContent: "center", pointerEvents: "none",
        }}>
          <span style={{ fontSize: "1.5rem", color: "var(--gm-blue)", fontWeight: 700 }}>Drop PDFs to upload</span>
        </div>
      )}

      <div style={{ marginBottom: "1.5rem", display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Papers</h1>
          <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Upload PDFs and audit R2 vs database coverage</p>
        </div>
        <button
          onClick={handleExportReport}
          disabled={exportingReport}
          style={{
            padding: "0.5rem 1rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)",
            borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: "pointer",
            display: "flex", alignItems: "center", gap: "0.4rem",
          }}
        >
          {exportingReport ? "Generating…" : "⬇ Export Full Audit Report (CSV)"}
        </button>
      </div>

      {/* Subject selector */}
      <div style={{ marginBottom: "1.5rem", display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
        <select
          value={selectedId}
          onChange={e => handleSubjectChange(e.target.value)}
          style={{ ...inputStyle, width: "auto", minWidth: "220px" }}
        >
          <option value="">— Select a subject —</option>
          {subjects.map(s => (
            <option key={s.id} value={s.id}>{s.level} · {s.name}{s.code ? ` (${s.code})` : ""}</option>
          ))}
        </select>
        {selectedId && (
          <button
            onClick={() => { setActiveTab("audit"); runAudit(selectedId) }}
            style={{ padding: "0.5rem 1rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text)", fontSize: "0.8rem", cursor: "pointer" }}
          >
            Run Audit
          </button>
        )}
        {selectedId && (
          <button
            onClick={handleSync}
            disabled={syncing}
            style={{ padding: "0.5rem 1rem", background: "var(--gm-blue)15", border: "1px solid var(--gm-blue)40", borderRadius: "0.5rem", color: "var(--gm-blue)", fontSize: "0.8rem", cursor: "pointer" }}
          >
            {syncing ? "Syncing…" : "Sync R2 → DB"}
          </button>
        )}
      </div>
      {syncMsg && (
        <div style={{ marginBottom: "1rem", padding: "0.625rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", fontSize: "0.8rem", color: "var(--gm-text-2)" }}>
          {syncMsg}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--gm-border)", marginBottom: "1.5rem" }}>
        {(["upload", "queue", "audit"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); if (tab === "audit" && selectedId) runAudit(selectedId) }}
            style={{
              padding: "0.625rem 1.25rem", fontSize: "0.8rem",
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? "var(--gm-text)" : "var(--gm-text-3)",
              borderBottom: activeTab === tab ? "2px solid var(--gm-blue)" : "2px solid transparent",
              background: "transparent", border: "none", cursor: "pointer", textTransform: "capitalize",
            }}
          >
            {tab}
            {tab === "audit" && missingCount > 0 && (
              <span style={{ marginLeft: "0.4rem", background: "#ef444430", color: "#ef4444", borderRadius: "0.25rem", padding: "0 0.35rem", fontSize: "0.65rem", fontWeight: 700 }}>
                {missingCount}
              </span>
            )}
            {tab === "queue" && queue.length > 0 && (
              <span style={{ marginLeft: "0.4rem", background: "var(--gm-blue)30", color: "var(--gm-blue)", borderRadius: "0.25rem", padding: "0 0.35rem", fontSize: "0.65rem", fontWeight: 700 }}>
                {queue.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Upload tab */}
      {activeTab === "upload" && (
        <form onSubmit={handleUpload} style={{ maxWidth: "520px" }}>
          {!selectedId && (
            <div style={{ marginBottom: "1rem", padding: "0.625rem 0.875rem", background: "#f59e0b10", border: "1px solid #f59e0b30", borderRadius: "0.5rem", fontSize: "0.78rem", color: "#f59e0b" }}>
              Select a subject above before uploading
            </div>
          )}

          {/* File dropzone */}
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={labelStyle}>PDF File <span style={{ color: "#ef4444" }}>*</span></label>
            <div
              onClick={() => document.getElementById("pdf-input")?.click()}
              style={{
                border: `2px dashed ${file ? "var(--gm-blue)" : "var(--gm-border)"}`,
                borderRadius: "0.75rem", padding: "2rem", textAlign: "center",
                cursor: "pointer", color: "var(--gm-text-3)", fontSize: "0.8rem",
                background: file ? "var(--gm-surface)" : "transparent", transition: "border-color 0.15s",
              }}
            >
              {file ? (
                <div>
                  <span style={{ color: "var(--gm-blue)", fontWeight: 600 }}>{file.name}</span>
                  <div style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.25rem" }}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB — click to change
                  </div>
                </div>
              ) : (
                <span>Click or drag-and-drop PDF files <span style={{ opacity: 0.6 }}>(single file fills fields below; multiple files go to queue)</span></span>
              )}
            </div>
            <input id="pdf-input" type="file" accept=".pdf" multiple style={{ display: "none" }}
              onChange={e => handleFilesSelected(e.target.files)} />
          </div>

          {/* Fields grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
            <div>
              <label style={labelStyle}>Year <span style={{ color: "#ef4444" }}>*</span></label>
              <input
                style={formErrors.year ? inputErrStyle : inputStyle}
                value={uploadYear}
                onChange={e => { setUploadYear(e.target.value); setFormErrors(p => ({ ...p, year: undefined })); setOverwriteWarning(null); setPendingSubmit(false) }}
                placeholder="2024" maxLength={4}
              />
              {formErrors.year && <div style={errMsgStyle}>{formErrors.year}</div>}
            </div>
            <div>
              <label style={labelStyle}>Session <span style={{ color: "#ef4444" }}>*</span></label>
              <select
                style={formErrors.session ? inputErrStyle : inputStyle}
                value={uploadSession}
                onChange={e => { setUploadSession(e.target.value); setFormErrors(p => ({ ...p, session: undefined })); setOverwriteWarning(null); setPendingSubmit(false) }}
              >
                <option value="">— Select —</option>
                {SEASONS.map(s => <option key={s} value={s}>{s === "Jan" ? "January" : s === "May-Jun" ? "May / June" : s === "Oct-Nov" ? "October / November" : s}</option>)}
              </select>
              {formErrors.session && <div style={errMsgStyle}>{formErrors.session}</div>}
            </div>
            <div>
              <label style={labelStyle}>Paper Number <span style={{ color: "#ef4444" }}>*</span></label>
              <input
                style={formErrors.paper ? inputErrStyle : inputStyle}
                value={uploadPaper}
                onChange={e => { setUploadPaper(e.target.value.toUpperCase()); setFormErrors(p => ({ ...p, paper: undefined })); setOverwriteWarning(null); setPendingSubmit(false) }}
                placeholder="1, 2, 1R, 3H…"
              />
              {formErrors.paper && <div style={errMsgStyle}>{formErrors.paper}</div>}
            </div>
            <div>
              <label style={labelStyle}>Type</label>
              <select style={inputStyle} value={uploadType} onChange={e => { setUploadType(e.target.value as "QP" | "MS"); setOverwriteWarning(null); setPendingSubmit(false) }}>
                <option value="QP">Question Paper (QP)</option>
                <option value="MS">Mark Scheme (MS)</option>
              </select>
            </div>
          </div>

          {/* Preview of R2 key */}
          {file && uploadYear && uploadSession && uploadPaper && (
            <div style={{ marginBottom: "1rem", padding: "0.5rem 0.75rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", fontSize: "0.7rem", color: "var(--gm-text-3)", fontFamily: "monospace" }}>
              R2 path: {(subjects.find(s => s.id === selectedId)?.name || "Subject").replace(/\s+/g, "_")}/{uploadYear}/{uploadSession}/…_{uploadPaper}_{uploadType}.pdf
            </div>
          )}

          {/* Overwrite warning */}
          {overwriteWarning && (
            <div style={{ marginBottom: "1rem", padding: "0.625rem 0.875rem", borderRadius: "0.5rem", fontSize: "0.8rem", background: "#f59e0b10", border: "1px solid #f59e0b40", color: "#f59e0b" }}>
              ⚠ {overwriteWarning}
            </div>
          )}

          {uploadMsg && (
            <div style={{
              marginBottom: "1rem", padding: "0.625rem 0.875rem", borderRadius: "0.5rem", fontSize: "0.8rem",
              background: uploadMsg.type === "ok" ? "#22c55e10" : "#ef444410",
              border: `1px solid ${uploadMsg.type === "ok" ? "#22c55e30" : "#ef444430"}`,
              color: uploadMsg.type === "ok" ? "#22c55e" : "#ef4444", wordBreak: "break-all",
            }}>
              {uploadMsg.text}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || !selectedId || uploading}
            style={{
              padding: "0.625rem 1.5rem",
              background: pendingSubmit ? "#f59e0b" : uploading ? "var(--gm-surface)" : "var(--gm-blue)",
              color: uploading ? "var(--gm-text-3)" : "#fff",
              borderRadius: "0.5rem", border: "none", fontSize: "0.875rem", fontWeight: 600,
              cursor: (!file || !selectedId || uploading) ? "not-allowed" : "pointer",
              opacity: (!file || !selectedId) ? 0.5 : 1, transition: "background 0.15s",
            }}
          >
            {uploading ? "Uploading…" : pendingSubmit ? "Click again to overwrite" : "Upload PDF"}
          </button>
        </form>
      )}

      {/* Queue tab */}
      {activeTab === "queue" && (
        <div>
          <div style={{ marginBottom: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
              {queue.length} files — {queuePending} pending, {queueDone} done{queueError > 0 ? `, ${queueError} errors` : ""}
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={() => document.getElementById("queue-input")?.click()}
                style={{ padding: "0.4rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-2)", fontSize: "0.78rem", cursor: "pointer" }}
              >
                + Add PDFs
              </button>
              <input id="queue-input" type="file" accept=".pdf" multiple style={{ display: "none" }}
                onChange={e => handleFilesSelected(e.target.files)} />
              {queue.filter(q => q.status !== "pending").length > 0 && (
                <button
                  onClick={() => setQueue(prev => prev.filter(q => q.status === "pending"))}
                  style={{ padding: "0.4rem 0.875rem", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.5rem", color: "var(--gm-text-3)", fontSize: "0.78rem", cursor: "pointer" }}
                >
                  Clear done
                </button>
              )}
              {!selectedId && <span style={{ fontSize: "0.78rem", color: "#f59e0b", alignSelf: "center" }}>Select subject first</span>}
              {queuePending > 0 && selectedId && (
                <button
                  onClick={handleUploadQueue}
                  disabled={uploadingAll}
                  style={{ padding: "0.4rem 1rem", background: "var(--gm-blue)", border: "none", borderRadius: "0.5rem", color: "#fff", fontSize: "0.78rem", fontWeight: 600, cursor: uploadingAll ? "not-allowed" : "pointer" }}
                >
                  {uploadingAll ? "Uploading…" : `Upload All (${queuePending})`}
                </button>
              )}
            </div>
          </div>

          {queue.length === 0 ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>
              No files in queue. Drag-and-drop multiple PDFs onto this page, or click &quot;+ Add PDFs&quot;.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {queue.map(item => (
                <div key={item.id} style={{
                  display: "grid", gridTemplateColumns: "1fr 80px 130px 80px 80px auto",
                  gap: "0.5rem", alignItems: "center",
                  padding: "0.625rem 0.75rem", borderRadius: "0.5rem",
                  background: "var(--gm-surface)", border: `1px solid ${item.status === "done" ? "#22c55e30" : item.status === "error" ? "#ef444430" : "var(--gm-border)"}`,
                  fontSize: "0.78rem",
                }}>
                  <span style={{ color: "var(--gm-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.file.name}</span>
                  <input
                    value={item.year}
                    onChange={e => setQueue(prev => prev.map(q => q.id === item.id ? { ...q, year: e.target.value } : q))}
                    placeholder="Year"
                    style={{ ...inputStyle, padding: "0.3rem 0.5rem", fontSize: "0.75rem" }}
                  />
                  <select
                    value={item.session}
                    onChange={e => setQueue(prev => prev.map(q => q.id === item.id ? { ...q, session: e.target.value } : q))}
                    style={{ ...inputStyle, padding: "0.3rem 0.5rem", fontSize: "0.75rem" }}
                  >
                    <option value="">Session</option>
                    {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <input
                    value={item.paper}
                    onChange={e => setQueue(prev => prev.map(q => q.id === item.id ? { ...q, paper: e.target.value.toUpperCase() } : q))}
                    placeholder="Paper"
                    style={{ ...inputStyle, padding: "0.3rem 0.5rem", fontSize: "0.75rem" }}
                  />
                  <select
                    value={item.type}
                    onChange={e => setQueue(prev => prev.map(q => q.id === item.id ? { ...q, type: e.target.value as "QP" | "MS" } : q))}
                    style={{ ...inputStyle, padding: "0.3rem 0.5rem", fontSize: "0.75rem" }}
                  >
                    <option value="QP">QP</option>
                    <option value="MS">MS</option>
                  </select>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    {item.status === "pending" && <span style={{ color: "var(--gm-text-3)" }}>—</span>}
                    {item.status === "uploading" && <span style={{ color: "var(--gm-blue)" }}>↑</span>}
                    {item.status === "done" && <span style={{ color: "#22c55e" }}>✓</span>}
                    {item.status === "error" && <span title={item.message} style={{ color: "#ef4444", cursor: "help" }}>✗</span>}
                    <button
                      onClick={() => setQueue(prev => prev.filter(q => q.id !== item.id))}
                      style={{ background: "none", border: "none", color: "var(--gm-text-3)", cursor: "pointer", padding: "0", fontSize: "0.9rem" }}
                      title="Remove from queue"
                    >×</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Audit tab */}
      {activeTab === "audit" && (
        <div>
          {auditLoading ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Loading audit…</div>
          ) : !selectedId ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Select a subject to run audit</div>
          ) : auditRows.length === 0 ? (
            <div style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>No data — click &quot;Run Audit&quot; above</div>
          ) : (
            <>
              <div style={{ marginBottom: "0.75rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
                  {subjectName} — {auditRows.length} paper sessions ·{" "}
                  <span style={{ color: missingCount > 0 ? "#ef4444" : "#22c55e", fontWeight: 600 }}>
                    {missingCount === 0 ? "all complete" : `${missingCount} incomplete`}
                  </span>
                </span>
                <div style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", display: "flex", gap: "1rem" }}>
                  <span><Dot ok={true} /> = present</span>
                  <span><Dot ok={false} /> = missing</span>
                </div>
              </div>

              {/* Filters */}
              <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                <select
                  value={filterStatus}
                  onChange={e => setFilterStatus(e.target.value as typeof filterStatus)}
                  style={{ ...inputStyle, width: "auto", fontSize: "0.75rem", padding: "0.35rem 0.6rem" }}
                >
                  <option value="all">All statuses</option>
                  <option value="incomplete">Any missing</option>
                  <option value="missing_both">Missing both QP + MS</option>
                  <option value="missing_qp">Missing QP only</option>
                  <option value="missing_ms">Missing MS only</option>
                </select>
                <select
                  value={filterYear}
                  onChange={e => setFilterYear(e.target.value)}
                  style={{ ...inputStyle, width: "auto", fontSize: "0.75rem", padding: "0.35rem 0.6rem" }}
                >
                  <option value="all">All years</option>
                  {allYears.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                {(filterStatus !== "all" || filterYear !== "all") && (
                  <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>
                    {filteredRows.length} of {auditRows.length} shown
                  </span>
                )}
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--gm-border)" }}>
                      {["Year", "Session", "Paper", "DB QP", "DB MS", "R2 QP", "R2 MS", "Actions"].map(h => (
                        <th key={h} style={{ padding: "0.5rem 0.75rem", textAlign: "left", color: "var(--gm-text-3)", fontWeight: 600, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row, i) => {
                      const complete = row.dbHasQP && row.dbHasMS && row.r2HasQP && row.r2HasMS
                      const dbComplete = row.dbHasQP && row.dbHasMS
                      const hasR2ButNoDb = (row.r2HasQP || row.r2HasMS) && !row.paperId
                      return (
                        <tr key={i} style={{
                          borderBottom: "1px solid var(--gm-border)",
                          background: complete ? "transparent" : dbComplete ? "#f59e0b06" : "#ef444406",
                        }}>
                          <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text)", fontWeight: 600 }}>{row.year}</td>
                          <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text-2)" }}>{row.season}</td>
                          <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text-2)", fontFamily: "monospace" }}>{row.paperNumber}</td>
                          <td style={{ padding: "0.5rem 0.75rem" }}><Dot ok={row.dbHasQP} /></td>
                          <td style={{ padding: "0.5rem 0.75rem" }}><Dot ok={row.dbHasMS} /></td>
                          <td style={{ padding: "0.5rem 0.75rem" }}><Dot ok={row.r2HasQP} /></td>
                          <td style={{ padding: "0.5rem 0.75rem" }}><Dot ok={row.r2HasMS} /></td>
                          <td style={{ padding: "0.5rem 0.75rem" }}>
                            <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                              {hasR2ButNoDb && (
                                <button
                                  onClick={() => handleAddToDB(row)}
                                  title="File exists in R2 but not in DB — add to DB"
                                  style={{ padding: "0.2rem 0.5rem", background: "var(--gm-blue)20", border: "1px solid var(--gm-blue)40", borderRadius: "0.25rem", color: "var(--gm-blue)", fontSize: "0.7rem", cursor: "pointer", whiteSpace: "nowrap" }}
                                >
                                  + Add to DB
                                </button>
                              )}
                              {row.paperId && (
                                <button
                                  onClick={() => handleDeletePaper(row)}
                                  disabled={deletingPaperId === row.paperId}
                                  title="Delete this paper record"
                                  style={{ padding: "0.2rem 0.5rem", background: "#ef444415", border: "1px solid #ef444430", borderRadius: "0.25rem", color: "#ef4444", fontSize: "0.7rem", cursor: "pointer" }}
                                >
                                  {deletingPaperId === row.paperId ? "…" : "Delete"}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
