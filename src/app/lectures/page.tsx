"use client"
import { useAuth } from "@/context/AuthContext"
import { supabase } from "@/lib/supabaseClient"
import { useCallback, useEffect, useState } from "react"
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

const FILE_ICONS: Record<string, string> = {
  "application/pdf": "📄",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "📊",
  "application/vnd.ms-powerpoint": "📊",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📝",
  "application/msword": "📝",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📋",
  "video/mp4": "🎬",
  "audio/mpeg": "🎵",
  "image/jpeg": "🖼",
  "image/png": "🖼",
}

export default function LecturesPage() {
  const { user, profile, loading: authLoading } = useAuth()
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [lectures, setLectures] = useState<Lecture[]>([])
  const [selectedSubject, setSelectedSubject] = useState<string>("")
  const [selectedWeek, setSelectedWeek] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  // Fetch subjects
  useEffect(() => {
    supabase.from("subjects").select("id, name, board, level").then(({ data }) => {
      setSubjects(data || [])
    })
  }, [])

  // Fetch lectures
  const fetchLectures = useCallback(async () => {
    setLoading(true)
    let url = "/api/lectures"
    const params = new URLSearchParams()
    if (selectedSubject) params.set("subject_id", selectedSubject)
    if (selectedWeek) params.set("week", selectedWeek)
    if (params.toString()) url += `?${params.toString()}`

    const res = await fetch(url)
    const data = await res.json()
    setLectures(data.lectures || [])
    setLoading(false)
  }, [selectedSubject, selectedWeek])

  useEffect(() => {
    if (user) fetchLectures()
  }, [user, fetchLectures])

  // Filter by search
  const filteredLectures = lectures.filter((l) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      l.lesson_name.toLowerCase().includes(q) ||
      l.file_name.toLowerCase().includes(q)
    )
  })

  // Group by subject → week → lesson
  const groupedBySubject = filteredLectures.reduce<
    Record<string, Record<number, Record<string, Lecture[]>>>
  >((acc, l) => {
    const subjectName = subjects.find((s) => s.id === l.subject_id)?.name || `Subject ${l.subject_id}`
    if (!acc[subjectName]) acc[subjectName] = {}
    if (!acc[subjectName][l.week_number]) acc[subjectName][l.week_number] = {}
    if (!acc[subjectName][l.week_number][l.lesson_name]) acc[subjectName][l.week_number][l.lesson_name] = []
    acc[subjectName][l.week_number][l.lesson_name].push(l)
    return acc
  }, {})

  const formatSize = (bytes: number | null) => {
    if (!bytes) return ""
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (type: string | null) => FILE_ICONS[type || ""] || "📎"

  // Get unique weeks for filter
  const availableWeeks = [...new Set(lectures.map((l) => l.week_number))].sort((a, b) => a - b)

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
          <p className="text-white/60 mb-4">Please sign in to view lectures.</p>
          <Link href="/login" className="rounded-lg bg-white text-black px-6 py-2 font-medium">Sign In</Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      <div className="max-w-5xl mx-auto py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">Lectures</h1>
            <p className="text-sm text-white/50 mt-1">Browse lecture materials uploaded by your teachers</p>
          </div>
          <div className="flex items-center gap-3">
            {profile && (profile.role === "teacher" || profile.role === "admin") && (
              <Link
                href="/dashboard/teacher"
                className="rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
              >
                Upload Lectures
              </Link>
            )}
            <Link
              href="/dashboard"
              className="rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
            >
              Dashboard
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/30"
          >
            <option value="" className="bg-black">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id} className="bg-black">
                {s.name} ({s.board} {s.level})
              </option>
            ))}
          </select>

          <select
            value={selectedWeek}
            onChange={(e) => setSelectedWeek(e.target.value)}
            className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/30"
          >
            <option value="" className="bg-black">All Weeks</option>
            {availableWeeks.map((w) => (
              <option key={w} value={w} className="bg-black">Week {w}</option>
            ))}
          </select>

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search lessons..."
            className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-white/30 flex-1 min-w-[200px]"
          />
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center py-16">
            <div className="animate-pulse text-white/50">Loading lectures...</div>
          </div>
        ) : filteredLectures.length === 0 ? (
          <div className="text-center py-16 rounded-2xl border border-white/10 bg-white/5">
            <div className="text-4xl mb-3">📚</div>
            <h2 className="text-lg font-semibold mb-1">No lectures found</h2>
            <p className="text-sm text-white/40">
              {selectedSubject || selectedWeek || searchQuery
                ? "Try adjusting your filters"
                : "Your teachers haven't uploaded any lectures yet"}
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {Object.entries(groupedBySubject)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([subjectName, weeks]) => (
                <div key={subjectName} className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
                  {/* Subject header */}
                  <div className="px-6 py-4 bg-white/5 border-b border-white/10">
                    <h2 className="text-lg font-semibold">{subjectName}</h2>
                  </div>

                  <div className="p-6 space-y-6">
                    {Object.entries(weeks)
                      .sort(([a], [b]) => parseInt(a) - parseInt(b))
                      .map(([week, lessons]) => (
                        <div key={week}>
                          <h3 className="text-sm font-semibold text-white/70 mb-3 flex items-center gap-2">
                            <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-white/10 text-xs font-bold">
                              {week}
                            </span>
                            Week {week}
                          </h3>
                          <div className="space-y-3 ml-9">
                            {Object.entries(lessons)
                              .sort(([a], [b]) => a.localeCompare(b))
                              .map(([lesson, files]) => (
                                <div key={lesson} className="rounded-lg bg-white/[0.03] border border-white/5 overflow-hidden">
                                  <div className="px-4 py-2.5 bg-white/5 border-b border-white/5">
                                    <h4 className="text-sm font-medium">{lesson}</h4>
                                  </div>
                                  <div className="divide-y divide-white/5">
                                    {files.map((file) => (
                                      <a
                                        key={file.id}
                                        href={file.file_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-white/5 transition-colors group"
                                      >
                                        <span className="text-lg">{getFileIcon(file.file_type)}</span>
                                        <span className="text-white/80 group-hover:text-white truncate flex-1">
                                          {file.file_name}
                                        </span>
                                        <span className="text-white/30 text-xs shrink-0">
                                          {formatSize(file.file_size)}
                                        </span>
                                        <span className="text-white/20 text-xs shrink-0">
                                          {new Date(file.created_at).toLocaleDateString()}
                                        </span>
                                      </a>
                                    ))}
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
    </main>
  )
}
