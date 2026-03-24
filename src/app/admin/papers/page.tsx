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
    borderRadius: "50%", background: ok ? "#22c55e" : "var(--gm-border)",
  }} />
)

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
  }

  const handleFileChange = (f: File | null) => {
    setFile(f)
    if (!f) return
    // Auto-detect from filename
    const name = f.name
    // Pattern: Subject_Year_Session_Paper_N_TYPE.pdf
    const m = name.match(/(\d{4})_([\w-]+)_Paper_([\w]+)_(QP|MS)\.pdf$/i)
    if (m) {
      setUploadYear(m[1])
      setUploadSession(m[2])
      setUploadPaper(m[3])
      setUploadType((m[4].toUpperCase() as "QP" | "MS"))
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !selectedId) return
    setUploading(true)
    setUploadMsg(null)
    const fd = new FormData()
    fd.append("file", file)
    fd.append("subject_id", selectedId)
    if (uploadYear) fd.append("year", uploadYear)
    if (uploadSession) fd.append("session", uploadSession)
    if (uploadPaper) fd.append("paper_number", uploadPaper)
    if (uploadType) fd.append("type", uploadType)
    const res = await fetch("/api/admin/papers/upload", { method: "POST", body: fd })
    const data = await res.json()
    if (res.ok) {
      setUploadMsg({ type: "ok", text: `Uploaded: ${data.r2Key}` })
      setFile(null)
      if (activeTab === "audit") runAudit(selectedId)
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
      setSyncMsg(`Scanned ${data.r2ObjectsScanned} R2 files. Inserted: ${data.inserted}, Updated: ${data.updated}`)
      runAudit(selectedId)
    } else {
      setSyncMsg(`Error: ${data.error}`)
    }
    setSyncing(false)
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
  const labelStyle: React.CSSProperties = { fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.25rem", display: "block" }

  const missingCount = auditRows.filter(r => !r.dbHasQP || !r.dbHasMS || !r.r2HasQP || !r.r2HasMS).length

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.25rem" }}>Papers</h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem" }}>Upload PDFs and audit R2 vs database coverage</p>
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
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={labelStyle}>PDF File</label>
            <div
              onClick={() => document.getElementById("pdf-input")?.click()}
              style={{
                border: "2px dashed var(--gm-border)",
                borderRadius: "0.75rem",
                padding: "2rem",
                textAlign: "center",
                cursor: "pointer",
                color: "var(--gm-text-3)",
                fontSize: "0.8rem",
                background: file ? "var(--gm-surface)" : "transparent",
              }}
            >
              {file ? (
                <span style={{ color: "var(--gm-blue)" }}>{file.name}</span>
              ) : (
                <span>Click to select PDF or drag &amp; drop</span>
              )}
            </div>
            <input id="pdf-input" type="file" accept=".pdf" style={{ display: "none" }}
              onChange={e => handleFileChange(e.target.files?.[0] || null)} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
            <div>
              <label style={labelStyle}>Year</label>
              <input style={inputStyle} value={uploadYear} onChange={e => setUploadYear(e.target.value)} placeholder="2024" />
            </div>
            <div>
              <label style={labelStyle}>Session</label>
              <select style={inputStyle} value={uploadSession} onChange={e => setUploadSession(e.target.value)}>
                <option value="">— Select —</option>
                <option value="Jan">January</option>
                <option value="May-Jun">May-June</option>
                <option value="Oct-Nov">October-November</option>
                <option value="Specimen">Specimen</option>
              </select>
            </div>
            <div>
              <label style={labelStyle}>Paper Number</label>
              <input style={inputStyle} value={uploadPaper} onChange={e => setUploadPaper(e.target.value)} placeholder="1, 2, 3H…" />
            </div>
            <div>
              <label style={labelStyle}>Type</label>
              <select style={inputStyle} value={uploadType} onChange={e => setUploadType(e.target.value as "QP" | "MS")}>
                <option value="QP">Question Paper (QP)</option>
                <option value="MS">Mark Scheme (MS)</option>
              </select>
            </div>
          </div>

          {uploadMsg && (
            <div style={{
              marginBottom: "1rem",
              padding: "0.625rem 0.875rem",
              borderRadius: "0.5rem",
              fontSize: "0.8rem",
              background: uploadMsg.type === "ok" ? "#22c55e10" : "#ef444410",
              border: `1px solid ${uploadMsg.type === "ok" ? "#22c55e30" : "#ef444430"}`,
              color: uploadMsg.type === "ok" ? "#22c55e" : "#ef4444",
            }}>
              {uploadMsg.text}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || !selectedId || uploading}
            style={{
              padding: "0.625rem 1.5rem",
              background: "var(--gm-blue)",
              color: "#fff",
              borderRadius: "0.5rem",
              border: "none",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: "pointer",
              opacity: (!file || !selectedId || uploading) ? 0.5 : 1,
            }}
          >
            {uploading ? "Uploading…" : "Upload PDF"}
          </button>
          {!selectedId && <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginTop: "0.5rem" }}>Select a subject above first</p>}
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
              <div style={{ marginBottom: "0.75rem", fontSize: "0.8rem", color: "var(--gm-text-3)" }}>
                {subjectName} — {auditRows.length} paper sessions · {missingCount} incomplete
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
                      return (
                        <tr key={i} style={{ borderBottom: "1px solid var(--gm-border)", background: complete ? "transparent" : "#ef444406" }}>
                          <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text)" }}>{row.year}</td>
                          <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text-2)" }}>{row.season}</td>
                          <td style={{ padding: "0.5rem 0.75rem", color: "var(--gm-text-2)" }}>{row.paperNumber}</td>
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
