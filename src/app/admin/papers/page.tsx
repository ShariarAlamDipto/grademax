"use client"
import { useEffect, useState, useCallback } from "react"

interface Subject { id: string; name: string; code: string | null; level: string }
interface AuditRow {
  year: number; season: string; paperNumber: string
  dbHasQP: boolean; dbHasMS: boolean; r2HasQP: boolean; r2HasMS: boolean
  r2QpKey: string | null; r2MsKey: string | null
}

const Dot = ({ ok }: { ok: boolean }) => (
  <span style={{
    display: "inline-block", width: "0.625rem", height: "0.625rem",
    borderRadius: "50%", background: ok ? "#22c55e" : "#ef444440",
    border: ok ? "none" : "1px solid #ef444460",
  }} />
)

const SEASONS = ["Jan", "May-Jun", "Oct-Nov", "Specimen"] as const

export default function PapersAdminPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedId, setSelectedId] = useState("")
  const [auditRows, setAuditRows] = useState<AuditRow[]>([])
  const [auditLoading, setAuditLoading] = useState(false)
  const [subjectName, setSubjectName] = useState("")

  // Upload form state
  const [file, setFile] = useState<File | null>(null)
  const [uploadType, setUploadType] = useState<"QP" | "MS">("QP")
  const [uploadYear, setUploadYear] = useState("")
  const [uploadSession, setUploadSession] = useState("")
  const [uploadPaper, setUploadPaper] = useState("")
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"upload" | "audit">("upload")
  const [exportingReport, setExportingReport] = useState(false)

  // Validation errors
  const [formErrors, setFormErrors] = useState<Partial<Record<"year" | "session" | "paper", string>>>({})

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
  }

  const handleFileChange = (f: File | null) => {
    setFile(f)
    setUploadMsg(null)
    if (!f) return
    // Auto-detect fields from filename: Subject_Year_Session_Paper_N_TYPE.pdf
    const m = f.name.match(/(\d{4})_(Jan|May-Jun|Oct-Nov)_Paper_([\w]+)_(QP|MS)\.pdf$/i)
    if (m) {
      setUploadYear(m[1])
      setUploadSession(m[2].charAt(0).toUpperCase() + m[2].slice(1))
      setUploadPaper(m[3])
      setUploadType(m[4].toUpperCase() as "QP" | "MS")
      setFormErrors({})
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

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !selectedId) return
    if (!validateForm()) return

    setUploading(true)
    setUploadMsg(null)
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
      setUploadMsg({ type: "ok", text: `✓ Uploaded successfully → ${data.r2Key}` })
      // Clear form fields after successful upload
      setFile(null)
      setUploadYear("")
      setUploadSession("")
      setUploadPaper("")
      setUploadType("QP")
      setFormErrors({})
      // Reset file input
      const input = document.getElementById("pdf-input") as HTMLInputElement
      if (input) input.value = ""
      // Refresh audit if it has data
      if (auditRows.length > 0) runAudit(selectedId)
    } else {
      setUploadMsg({ type: "err", text: data.error || "Upload failed" })
    }
    setUploading(false)
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

  // Export missing papers report as CSV
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
      const a = document.createElement("a")
      a.href = url
      a.download = `grademax-papers-audit-${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert("Export failed")
    } finally {
      setExportingReport(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    background: "var(--gm-bg)",
    border: "1px solid var(--gm-border)",
    borderRadius: "0.5rem",
    padding: "0.5rem 0.75rem",
    color: "var(--gm-text)",
    fontSize: "0.8rem",
    width: "100%",
    outline: "none",
  }
  const inputErrStyle: React.CSSProperties = { ...inputStyle, borderColor: "#ef4444" }
  const labelStyle: React.CSSProperties = { fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.25rem", display: "block" }
  const errMsgStyle: React.CSSProperties = { fontSize: "0.7rem", color: "#ef4444", marginTop: "0.2rem" }

  const missingCount = auditRows.filter(r => !r.dbHasQP || !r.dbHasMS || !r.r2HasQP || !r.r2HasMS).length

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px" }}>
      <div style={{ marginBottom: "1.5rem", display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Papers</h1>
          <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Upload PDFs and audit R2 vs database coverage</p>
        </div>
        <button
          onClick={handleExportReport}
          disabled={exportingReport}
          style={{
            padding: "0.5rem 1rem",
            background: "var(--gm-surface)",
            border: "1px solid var(--gm-border)",
            borderRadius: "0.5rem",
            color: "var(--gm-text-2)",
            fontSize: "0.78rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
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
        {(["upload", "audit"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); if (tab === "audit" && selectedId) runAudit(selectedId) }}
            style={{
              padding: "0.625rem 1.25rem",
              fontSize: "0.8rem",
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? "var(--gm-text)" : "var(--gm-text-3)",
              borderBottom: activeTab === tab ? "2px solid var(--gm-blue)" : "2px solid transparent",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {tab}
            {tab === "audit" && missingCount > 0 && (
              <span style={{ marginLeft: "0.4rem", background: "#ef444430", color: "#ef4444", borderRadius: "0.25rem", padding: "0 0.35rem", fontSize: "0.65rem", fontWeight: 700 }}>
                {missingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Upload tab */}
      {activeTab === "upload" && (
        <form onSubmit={handleUpload} style={{ maxWidth: "520px" }}>
          {/* Subject required notice */}
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
                borderRadius: "0.75rem",
                padding: "2rem",
                textAlign: "center",
                cursor: "pointer",
                color: "var(--gm-text-3)",
                fontSize: "0.8rem",
                background: file ? "var(--gm-surface)" : "transparent",
                transition: "border-color 0.15s",
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
                <span>Click to select PDF <span style={{ opacity: 0.6 }}>(filename will auto-fill fields below)</span></span>
              )}
            </div>
            <input id="pdf-input" type="file" accept=".pdf" style={{ display: "none" }}
              onChange={e => handleFileChange(e.target.files?.[0] || null)} />
          </div>

          {/* Fields grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
            <div>
              <label style={labelStyle}>Year <span style={{ color: "#ef4444" }}>*</span></label>
              <input
                style={formErrors.year ? inputErrStyle : inputStyle}
                value={uploadYear}
                onChange={e => { setUploadYear(e.target.value); setFormErrors(p => ({ ...p, year: undefined })) }}
                placeholder="2024"
                maxLength={4}
              />
              {formErrors.year && <div style={errMsgStyle}>{formErrors.year}</div>}
            </div>
            <div>
              <label style={labelStyle}>Session <span style={{ color: "#ef4444" }}>*</span></label>
              <select
                style={formErrors.session ? inputErrStyle : inputStyle}
                value={uploadSession}
                onChange={e => { setUploadSession(e.target.value); setFormErrors(p => ({ ...p, session: undefined })) }}
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
                onChange={e => { setUploadPaper(e.target.value.toUpperCase()); setFormErrors(p => ({ ...p, paper: undefined })) }}
                placeholder="1, 2, 1R, 3H…"
              />
              {formErrors.paper && <div style={errMsgStyle}>{formErrors.paper}</div>}
            </div>
            <div>
              <label style={labelStyle}>Type</label>
              <select style={inputStyle} value={uploadType} onChange={e => setUploadType(e.target.value as "QP" | "MS")}>
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

          {uploadMsg && (
            <div style={{
              marginBottom: "1rem",
              padding: "0.625rem 0.875rem",
              borderRadius: "0.5rem",
              fontSize: "0.8rem",
              background: uploadMsg.type === "ok" ? "#22c55e10" : "#ef444410",
              border: `1px solid ${uploadMsg.type === "ok" ? "#22c55e30" : "#ef444430"}`,
              color: uploadMsg.type === "ok" ? "#22c55e" : "#ef4444",
              wordBreak: "break-all",
            }}>
              {uploadMsg.text}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || !selectedId || uploading}
            style={{
              padding: "0.625rem 1.5rem",
              background: uploading ? "var(--gm-surface)" : "var(--gm-blue)",
              color: uploading ? "var(--gm-text-3)" : "#fff",
              borderRadius: "0.5rem",
              border: "none",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: (!file || !selectedId || uploading) ? "not-allowed" : "pointer",
              opacity: (!file || !selectedId) ? 0.5 : 1,
              transition: "background 0.15s",
            }}
          >
            {uploading ? "Uploading…" : "Upload PDF"}
          </button>
        </form>
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
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--gm-border)" }}>
                      {["Year", "Session", "Paper", "DB QP", "DB MS", "R2 QP", "R2 MS"].map(h => (
                        <th key={h} style={{ padding: "0.5rem 0.75rem", textAlign: "left", color: "var(--gm-text-3)", fontWeight: 600, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {auditRows.map((row, i) => {
                      const complete = row.dbHasQP && row.dbHasMS && row.r2HasQP && row.r2HasMS
                      const dbComplete = row.dbHasQP && row.dbHasMS
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
