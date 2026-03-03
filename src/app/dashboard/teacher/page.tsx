"use client"
import { useAuth } from "@/context/AuthContext"
import { supabase } from "@/lib/supabaseClient"
import { useCallback, useEffect, useState, useRef } from "react"
import Link from "next/link"

const SUPER_ADMIN_EMAIL = "shariardipto111@gmail.com"

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
}

export default function TeacherDashboardPage() {
  const { user, profile, displayName, loading: authLoading } = useAuth()
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [lectures, setLectures] = useState<Lecture[]>([])
  const [selectedSubject, setSelectedSubject] = useState<string>("")
  const [weekNumber, setWeekNumber] = useState<number>(1)
  const [lessonName, setLessonName] = useState("")
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadQueue, setUploadQueue] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState<string[]>([])
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loadingLectures, setLoadingLectures] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch subjects
  useEffect(() => {
    supabase.from("subjects").select("id, name, board, level").then(({ data }) => {
      setSubjects(data || [])
    })
  }, [])

  // Fetch lectures for selected subject
  const fetchLectures = useCallback(async () => {
    if (!selectedSubject) return
    setLoadingLectures(true)
    try {
      const res = await fetch(`/api/lectures?subject_id=${selectedSubject}`)
      if (!res.ok) throw new Error(`Server error (${res.status})`)
      const data = await res.json()
      setLectures(data.lectures || [])
    } catch (err) {
      console.error("Failed to fetch lectures:", err)
      setLectures([])
    } finally {
      setLoadingLectures(false)
    }
  }, [selectedSubject])

  useEffect(() => {
    fetchLectures()
  }, [fetchLectures])

  // Drag and drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      setUploadQueue((prev) => [...prev, ...files])
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      setUploadQueue((prev) => [...prev, ...files])
    }
  }, [])

  const removeFromQueue = (index: number) => {
    setUploadQueue((prev) => prev.filter((_, i) => i !== index))
  }

  // Upload all files
  const handleUpload = async () => {
    if (!selectedSubject || !lessonName.trim() || uploadQueue.length === 0) {
      setError("Please select a subject, enter a lesson name, and add files")
      return
    }

    setUploading(true)
    setError("")
    setSuccess("")
    setUploadProgress([])
    const progressMessages: string[] = []

    for (const file of uploadQueue) {
      progressMessages.push(`Uploading ${file.name}...`)
      setUploadProgress([...progressMessages])

      const formData = new FormData()
      formData.append("file", file)
      formData.append("subject_id", selectedSubject)
      formData.append("week_number", weekNumber.toString())
      formData.append("lesson_name", lessonName.trim())

      const res = await fetch("/api/lectures/upload", {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        progressMessages[progressMessages.length - 1] = `✗ ${file.name}: ${err.error}`
        setUploadProgress([...progressMessages])
      } else {
        progressMessages[progressMessages.length - 1] = `✓ ${file.name} uploaded`
        setUploadProgress([...progressMessages])
      }
    }

    setUploading(false)
    setSuccess("Upload complete!")
    setUploadQueue([])
    setLessonName("")
    if (fileInputRef.current) fileInputRef.current.value = ""
    fetchLectures()
  }

  // Delete a lecture
  const handleDelete = async (lectureId: string) => {
    if (!confirm("Delete this lecture file?")) return
    const res = await fetch(`/api/lectures/${lectureId}`, { method: "DELETE" })
    if (res.ok) {
      fetchLectures()
    }
  }

  // Format file size
  const formatSize = (bytes: number | null) => {
    if (!bytes) return "—"
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Group lectures by week → lesson
  const groupedLectures = lectures.reduce<Record<number, Record<string, Lecture[]>>>((acc, l) => {
    if (!acc[l.week_number]) acc[l.week_number] = {}
    if (!acc[l.week_number][l.lesson_name]) acc[l.week_number][l.lesson_name] = []
    acc[l.week_number][l.lesson_name].push(l)
    return acc
  }, {})

  if (authLoading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="animate-pulse text-white/50">Loading...</div>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-white/60 mb-4">Please sign in to access the teacher dashboard.</p>
          <Link href="/login" className="rounded-lg bg-white text-black px-6 py-2 font-medium">
            Sign In
          </Link>
        </div>
      </main>
    )
  }

  const isSuperAdminUser = user?.email?.toLowerCase() === SUPER_ADMIN_EMAIL.toLowerCase()

  if (profile && profile.role !== "teacher" && profile.role !== "admin" && !isSuperAdminUser) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-4xl mb-4">🔒</div>
          <h1 className="text-xl font-bold mb-2">Teacher Access Required</h1>
          <p className="text-white/60 mb-4">
            You need teacher access to upload lectures. Ask your administrator to grant you access.
          </p>
          <Link href="/dashboard" className="rounded-lg bg-white/10 px-6 py-2 text-sm hover:bg-white/15">
            Back to Dashboard
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      <div className="max-w-5xl mx-auto py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">Teacher Dashboard</h1>
            <p className="text-sm text-white/50 mt-1">Welcome, {displayName} — Upload and manage your lectures</p>
          </div>
          <Link
            href="/dashboard"
            className="rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
          >
            Student View
          </Link>
        </div>

        <div className="grid gap-8 lg:grid-cols-5">
          {/* Upload Panel - Left */}
          <div className="lg:col-span-2 space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-lg font-semibold mb-4">Upload Lecture</h2>

              {/* Subject selector */}
              <div className="mb-4">
                <label className="block text-sm text-white/70 mb-1">Subject</label>
                <select
                  value={selectedSubject}
                  onChange={(e) => setSelectedSubject(e.target.value)}
                  className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/30"
                >
                  <option value="" className="bg-black">Select subject...</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id} className="bg-black">
                      {s.name} ({s.board} {s.level})
                    </option>
                  ))}
                </select>
              </div>

              {/* Week number */}
              <div className="mb-4">
                <label className="block text-sm text-white/70 mb-1">Week Number</label>
                <input
                  type="number"
                  min={1}
                  max={52}
                  value={weekNumber}
                  onChange={(e) => setWeekNumber(parseInt(e.target.value) || 1)}
                  className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/30"
                />
              </div>

              {/* Lesson name */}
              <div className="mb-4">
                <label className="block text-sm text-white/70 mb-1">Lesson Name</label>
                <input
                  type="text"
                  value={lessonName}
                  onChange={(e) => setLessonName(e.target.value)}
                  placeholder="e.g. Introduction to Kinematics"
                  className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-white/30"
                />
              </div>

              {/* Drag and Drop Zone */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
                  dragActive
                    ? "border-white bg-white/10"
                    : "border-white/20 hover:border-white/40 hover:bg-white/5"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.pptx,.ppt,.doc,.docx,.xlsx,.xls,.jpg,.jpeg,.png,.gif,.mp4,.mp3,.zip"
                />
                <div className="text-3xl mb-2">📁</div>
                <p className="text-sm text-white/70">
                  {dragActive ? "Drop files here..." : "Drag & drop files here"}
                </p>
                <p className="text-xs text-white/40 mt-1">or click to browse</p>
                <p className="text-xs text-white/30 mt-2">
                  PDF, PPTX, DOC, XLSX, Images, Videos
                </p>
              </div>

              {/* Upload Queue */}
              {uploadQueue.length > 0 && (
                <div className="mt-4 space-y-2">
                  <p className="text-sm text-white/70 font-medium">Files to upload:</p>
                  {uploadQueue.map((file, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm"
                    >
                      <span className="truncate mr-2">{file.name}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-white/40 text-xs">{formatSize(file.size)}</span>
                        <button
                          onClick={() => removeFromQueue(i)}
                          className="text-red-400 hover:text-red-300 text-xs"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Upload Progress */}
              {uploadProgress.length > 0 && (
                <div className="mt-4 space-y-1">
                  {uploadProgress.map((msg, i) => (
                    <p key={i} className={`text-xs ${msg.startsWith("✓") ? "text-green-400" : msg.startsWith("✗") ? "text-red-400" : "text-white/50"}`}>
                      {msg}
                    </p>
                  ))}
                </div>
              )}

              {/* Error / Success */}
              {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
              {success && <p className="mt-3 text-sm text-green-400">{success}</p>}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={uploading || uploadQueue.length === 0}
                className={`mt-4 w-full rounded-lg py-2.5 text-sm font-medium transition-colors ${
                  uploading || uploadQueue.length === 0
                    ? "bg-white/10 text-white/30 cursor-not-allowed"
                    : "bg-white text-black hover:bg-white/90"
                }`}
              >
                {uploading ? "Uploading..." : `Upload ${uploadQueue.length} file${uploadQueue.length !== 1 ? "s" : ""}`}
              </button>
            </div>
          </div>

          {/* Lecture List - Right */}
          <div className="lg:col-span-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-lg font-semibold mb-4">
                Uploaded Lectures
                {selectedSubject && (
                  <span className="text-sm text-white/50 font-normal ml-2">
                    — {subjects.find((s) => s.id === selectedSubject)?.name}
                  </span>
                )}
              </h2>

              {!selectedSubject ? (
                <p className="text-sm text-white/40 text-center py-8">
                  Select a subject to view uploaded lectures
                </p>
              ) : loadingLectures ? (
                <div className="text-center py-8">
                  <div className="animate-pulse text-white/50">Loading lectures...</div>
                </div>
              ) : Object.keys(groupedLectures).length === 0 ? (
                <p className="text-sm text-white/40 text-center py-8">
                  No lectures uploaded yet for this subject
                </p>
              ) : (
                <div className="space-y-6">
                  {Object.entries(groupedLectures)
                    .sort(([a], [b]) => parseInt(a) - parseInt(b))
                    .map(([week, lessons]) => (
                      <div key={week}>
                        <h3 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
                          <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-white/10 text-xs">
                            {week}
                          </span>
                          Week {week}
                        </h3>
                        <div className="space-y-3 ml-9">
                          {Object.entries(lessons)
                            .sort(([a], [b]) => a.localeCompare(b))
                            .map(([lesson, files]) => (
                              <div key={lesson} className="rounded-lg bg-white/5 border border-white/5 overflow-hidden">
                                <div className="px-4 py-2 bg-white/5 border-b border-white/5">
                                  <h4 className="text-sm font-medium">{lesson}</h4>
                                </div>
                                <div className="divide-y divide-white/5">
                                  {files.map((file) => (
                                    <div key={file.id} className="flex items-center justify-between px-4 py-2 text-sm">
                                      <a
                                        href={file.file_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-400 hover:text-blue-300 truncate mr-3"
                                      >
                                        {file.file_name}
                                      </a>
                                      <div className="flex items-center gap-3 shrink-0">
                                        <span className="text-white/30 text-xs">
                                          {formatSize(file.file_size)}
                                        </span>
                                        <button
                                          onClick={() => handleDelete(file.id)}
                                          className="text-red-400/60 hover:text-red-400 text-xs"
                                          title="Delete"
                                        >
                                          🗑
                                        </button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
