"use client"
import { useAuth } from "@/context/AuthContext"
import { supabase } from "@/lib/supabaseClient"
import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"

interface Subject {
  id: string
  name: string
  board: string
  level: string
}

interface Lecture {
  id: string
  subject_id: string
  week_number: number
  lesson_name: string
  file_name: string
  file_url: string
  file_size: number | null
  file_type: string | null
  created_at: string
  subjects?: { id: string; name: string; board: string; level: string }
}

function getFileIcon(type: string | null): string {
  if (!type) return "📎"
  if (type.includes("pdf")) return "PDF"
  if (type.includes("presentation") || type.includes("powerpoint")) return "PPT"
  if (type.includes("word")) return "DOC"
  if (type.includes("sheet")) return "XLS"
  if (type.includes("video")) return "VID"
  if (type.includes("audio")) return "AUD"
  if (type.includes("image")) return "IMG"
  return "FILE"
}

function formatSize(bytes: number | null): string {
  if (!bytes) return ""
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function LecturesPage() {
  const { user, isTeacher, loading: authLoading } = useAuth()
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [lectures, setLectures] = useState<Lecture[]>([])
  const [selectedSubject, setSelectedSubject] = useState<string>("")
  const [selectedWeek, setSelectedWeek] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [initialLoadDone, setInitialLoadDone] = useState(false)
  const [collapsedSubjects, setCollapsedSubjects] = useState<Set<string>>(new Set())
  const [collapsedWeeks, setCollapsedWeeks] = useState<Set<string>>(new Set())

  const toggleSubject = useCallback((name: string) => {
    setCollapsedSubjects((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }, [])

  const toggleWeek = useCallback((key: string) => {
    setCollapsedWeeks((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }, [])

  useEffect(() => {
    supabase.from("subjects").select("id, name, board, level").then(({ data }) => {
      setSubjects(data || [])
    })
  }, [])

  const fetchLectures = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      let url = "/api/lectures"
      const params = new URLSearchParams()
      if (selectedSubject) params.set("subject_id", selectedSubject)
      if (selectedWeek) params.set("week", selectedWeek)
      if (params.toString()) url += `?${params.toString()}`
      const res = await fetch(url, { signal })
      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.error || `Server error (${res.status})`)
      }
      const data = await res.json()
      setLectures(data.lectures || [])
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "Failed to load lectures")
      setLectures([])
    } finally {
      setLoading(false)
      setInitialLoadDone(true)
    }
  }, [selectedSubject, selectedWeek])

  useEffect(() => {
    if (authLoading || !user) return
    const controller = new AbortController()
    fetchLectures(controller.signal)
    return () => controller.abort()
  }, [user, authLoading, fetchLectures])

  const filteredLectures = useMemo(() => lectures.filter((l) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return l.lesson_name.toLowerCase().includes(q) || l.file_name.toLowerCase().includes(q)
  }), [lectures, searchQuery])

  const groupedBySubject = useMemo(() => filteredLectures.reduce<
    Record<string, Record<number, Record<string, Lecture[]>>>
  >((acc, l) => {
    const subjectName = subjects.find((s) => s.id === l.subject_id)?.name || `Subject ${l.subject_id}`
    if (!acc[subjectName]) acc[subjectName] = {}
    if (!acc[subjectName][l.week_number]) acc[subjectName][l.week_number] = {}
    if (!acc[subjectName][l.week_number][l.lesson_name]) acc[subjectName][l.week_number][l.lesson_name] = []
    acc[subjectName][l.week_number][l.lesson_name].push(l)
    return acc
  }, {}), [filteredLectures, subjects])

  const availableWeeks = useMemo(() =>
    [...new Set(lectures.map((l) => l.week_number))].sort((a, b) => a - b),
    [lectures]
  )

  const inputStyle: React.CSSProperties = {
    background: "var(--gm-surface)",
    border: "1px solid var(--gm-border-2)",
    borderRadius: "0.625rem",
    color: "var(--gm-text)",
    padding: "0.5rem 0.875rem",
    fontSize: "0.875rem",
    outline: "none",
  }

  if (authLoading) {
    return (
      <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--gm-text-3)", animation: "pulse 2s infinite" }}>Loading…</div>
      </main>
    )
  }

  if (!user) {
    return (
      <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "var(--gm-text-3)", marginBottom: "1rem", fontSize: "0.9rem" }}>Verifying your session…</div>
          <p style={{ color: "var(--gm-text-3)", fontSize: "0.82rem" }}>
            If this takes too long,{" "}
            <Link href="/login?next=/lectures" style={{ color: "var(--gm-blue)", textDecoration: "underline" }}>sign in here</Link>.
          </p>
        </div>
      </main>
    )
  }

  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh", padding: "0 1.5rem 4rem" }}>
      <div style={{ maxWidth: "900px", margin: "0 auto", paddingTop: "2.5rem" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "2rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <p style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.4rem" }}>
              GradeMax
            </p>
            <h1 style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.4rem" }}>
              Lectures
            </h1>
            <p style={{ fontSize: "0.85rem", color: "var(--gm-text-3)" }}>
              Browse materials uploaded by your teachers.
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            {isTeacher && (
              <Link
                href="/dashboard/teacher"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "0.5rem 1rem",
                  borderRadius: "0.625rem",
                  border: "1px solid var(--gm-blue-ring)",
                  background: "var(--gm-blue-bg)",
                  color: "var(--gm-blue)",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  textDecoration: "none",
                  transition: "background 0.15s",
                }}
              >
                Upload Lectures
              </Link>
            )}
            <Link
              href="/dashboard"
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "0.5rem 1rem",
                borderRadius: "0.625rem",
                border: "1px solid var(--gm-border-2)",
                background: "var(--gm-card-bg)",
                color: "var(--gm-text-2)",
                fontSize: "0.82rem",
                fontWeight: 500,
                textDecoration: "none",
                transition: "background 0.15s",
              }}
            >
              Dashboard
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "2rem" }}>
          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            style={{ ...inputStyle, minWidth: "160px" }}
          >
            <option value="">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.board} {s.level})
              </option>
            ))}
          </select>

          <select
            value={selectedWeek}
            onChange={(e) => setSelectedWeek(e.target.value)}
            style={{ ...inputStyle, minWidth: "130px" }}
          >
            <option value="">All Weeks</option>
            {availableWeeks.map((w) => (
              <option key={w} value={w}>Week {w}</option>
            ))}
          </select>

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search lessons…"
            style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
          />
        </div>

        {/* Content */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "5rem 0", color: "var(--gm-text-3)" }}>
            Loading lectures…
          </div>
        ) : error ? (
          <div style={{ textAlign: "center", padding: "3rem", borderRadius: "1rem", border: "1px solid rgba(239,68,68,0.2)", background: "rgba(239,68,68,0.05)" }}>
            <p style={{ fontSize: "1rem", fontWeight: 600, color: "#EF4444", marginBottom: "0.5rem" }}>Failed to load lectures</p>
            <p style={{ fontSize: "0.82rem", color: "var(--gm-text-3)", marginBottom: "1rem" }}>{error}</p>
            <button
              onClick={() => fetchLectures()}
              style={{ padding: "0.5rem 1.25rem", borderRadius: "0.625rem", border: "1px solid var(--gm-border-2)", background: "var(--gm-card-bg)", color: "var(--gm-text)", fontSize: "0.82rem", cursor: "pointer" }}
            >
              Try Again
            </button>
          </div>
        ) : !initialLoadDone || filteredLectures.length === 0 ? (
          <div style={{ textAlign: "center", padding: "5rem 0", color: "var(--gm-text-3)" }}>
            <p style={{ fontSize: "1rem", fontWeight: 600, color: "var(--gm-text-2)", marginBottom: "0.4rem" }}>
              {!initialLoadDone ? "Loading…" : "No lectures found"}
            </p>
            <p style={{ fontSize: "0.82rem" }}>
              {selectedSubject || selectedWeek || searchQuery
                ? "Try adjusting your filters."
                : "Your teachers haven't uploaded any lectures yet."}
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {Object.entries(groupedBySubject)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([subjectName, weeks]) => {
                const subjectCollapsed = collapsedSubjects.has(subjectName)
                const fileCount = Object.values(weeks).reduce((sum, lessons) =>
                  sum + Object.values(lessons).reduce((s, f) => s + f.length, 0), 0)
                return (
                  <div key={subjectName} style={{ background: "var(--gm-card-bg)", border: "1px solid var(--gm-border-2)", borderRadius: "1rem", overflow: "hidden" }}>
                    {/* Subject header */}
                    <button
                      type="button"
                      onClick={() => toggleSubject(subjectName)}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "1rem 1.25rem",
                        background: "var(--gm-surface)",
                        borderBottom: "1px solid var(--gm-border)",
                        cursor: "pointer",
                        textAlign: "left",
                        color: "var(--gm-text)",
                      }}
                    >
                      <h2 style={{ fontSize: "0.95rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", margin: 0 }}>
                        <span style={{ color: "var(--gm-text-3)", fontSize: "0.7rem", transform: subjectCollapsed ? "none" : "rotate(90deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
                        {subjectName}
                      </h2>
                      <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)" }}>{fileCount} file{fileCount !== 1 ? "s" : ""}</span>
                    </button>

                    {!subjectCollapsed && (
                      <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                        {Object.entries(weeks)
                          .sort(([a], [b]) => parseInt(a) - parseInt(b))
                          .map(([week, lessons]) => {
                            const weekKey = `${subjectName}__${week}`
                            const weekCollapsed = collapsedWeeks.has(weekKey)
                            const weekFileCount = Object.values(lessons).reduce((s, f) => s + f.length, 0)
                            return (
                              <div key={week}>
                                <button
                                  type="button"
                                  onClick={() => toggleWeek(weekKey)}
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.5rem",
                                    width: "100%",
                                    textAlign: "left",
                                    background: "none",
                                    border: "none",
                                    cursor: "pointer",
                                    color: "var(--gm-text-2)",
                                    marginBottom: "0.75rem",
                                    padding: 0,
                                  }}
                                >
                                  <span style={{ color: "var(--gm-text-3)", fontSize: "0.65rem", transform: weekCollapsed ? "none" : "rotate(90deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
                                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "24px", height: "24px", borderRadius: "50%", background: "var(--gm-blue-bg)", fontSize: "0.7rem", fontWeight: 700, color: "var(--gm-blue)" }}>
                                    {week}
                                  </span>
                                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Week {week}</span>
                                  <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginLeft: "auto" }}>{weekFileCount} file{weekFileCount !== 1 ? "s" : ""}</span>
                                </button>

                                {!weekCollapsed && (
                                  <div style={{ marginLeft: "2rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                    {Object.entries(lessons)
                                      .sort(([a], [b]) => a.localeCompare(b))
                                      .map(([lesson, files]) => (
                                        <div key={lesson} style={{ background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "0.75rem", overflow: "hidden" }}>
                                          <div style={{ padding: "0.625rem 1rem", background: "var(--gm-surface-2)", borderBottom: "1px solid var(--gm-border)" }}>
                                            <h4 style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gm-text)", margin: 0 }}>{lesson}</h4>
                                          </div>
                                          <div>
                                            {files.map((file) => (
                                              <a
                                                key={file.id}
                                                href={file.file_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{
                                                  display: "flex",
                                                  alignItems: "center",
                                                  gap: "0.75rem",
                                                  padding: "0.625rem 1rem",
                                                  borderBottom: "1px solid var(--gm-border)",
                                                  textDecoration: "none",
                                                  transition: "background 0.15s",
                                                }}
                                                className="gm-link"
                                              >
                                                <span style={{
                                                  fontSize: "0.55rem",
                                                  fontWeight: 800,
                                                  letterSpacing: "0.04em",
                                                  padding: "0.2rem 0.4rem",
                                                  borderRadius: "4px",
                                                  background: "var(--gm-blue-bg)",
                                                  color: "var(--gm-blue)",
                                                  border: "1px solid var(--gm-blue-ring)",
                                                  flexShrink: 0,
                                                }}>
                                                  {getFileIcon(file.file_type)}
                                                </span>
                                                <span style={{ fontSize: "0.82rem", color: "var(--gm-text-2)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                                  {file.file_name}
                                                </span>
                                                <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", flexShrink: 0 }}>
                                                  {formatSize(file.file_size)}
                                                </span>
                                                <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", flexShrink: 0 }}>
                                                  {new Date(file.created_at).toLocaleDateString()}
                                                </span>
                                              </a>
                                            ))}
                                          </div>
                                        </div>
                                      ))}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                      </div>
                    )}
                  </div>
                )
              })}
          </div>
        )}
      </div>
    </main>
  )
}
