"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabaseClient"
import {
  addSubject, countPapers, listAllSubjects, listCompletions, listMySubjectIds, removeSubject,
  type CompletionRecord, type SubjectOption,
} from "@/lib/dashboard/studentData"
import { completionPoints } from "@/lib/rewards/points"
import { SubjectPapers } from "./SubjectPapers"
import { SubjectLeaderboard } from "./SubjectLeaderboard"
import "./dashboard-refresh.css"

/**
 * "My subjects": the student adds the subjects they sit, ticks off completed
 * papers for progression points, and competes on each subject's leaderboard.
 */

interface SubjectsBoardProps {
  userId: string
}

type Tab = "papers" | "leaderboard"

const MAX_MATCHES = 8

function levelLabel(level: string | null): string {
  const value = (level ?? "").toLowerCase()
  if (value === "igcse") return "IGCSE / O Level"
  if (value === "ial") return "A Level (IAL)"
  return level ?? ""
}

export function SubjectsBoard({ userId }: SubjectsBoardProps) {
  const router = useRouter()
  const [allSubjects, setAllSubjects] = useState<SubjectOption[]>([])
  const [myIds, setMyIds] = useState<string[]>([])
  const [paperCounts, setPaperCounts] = useState<Record<string, number>>({})
  const [completions, setCompletions] = useState<CompletionRecord[]>([])
  const [progressAvailable, setProgressAvailable] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("papers")
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [subjects, mine, done] = await Promise.all([
        listAllSubjects(supabase), listMySubjectIds(supabase, userId), listCompletions(supabase, userId),
      ])
      if (cancelled) return
      if (subjects.ok) setAllSubjects(subjects.data)
      else setMessage("Your subjects could not be loaded. Reload the page to try again.")
      if (mine.ok) {
        setMyIds(mine.data)
        setSelectedId(current => current ?? mine.data[0] ?? null)
        setPaperCounts(await countPapers(supabase, mine.data))
      }
      if (done.ok) setCompletions(done.data)
      else setProgressAvailable(!done.unavailable)
      setLoading(false)
    }
    void load()
    return () => { cancelled = true }
  }, [userId])

  const mySubjects = useMemo(
    () => myIds.map(id => allSubjects.find(s => s.id === id)).filter((s): s is SubjectOption => Boolean(s)),
    [myIds, allSubjects],
  )

  const matches = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    if (words.length === 0) return []
    return allSubjects
      .filter(s => !myIds.includes(s.id))
      .filter(s => {
        const text = `${s.name} ${s.code ?? ""} ${s.level ?? ""} ${s.board ?? ""}`.toLowerCase()
        return words.every(word => text.includes(word))
      })
      .slice(0, MAX_MATCHES)
  }, [query, allSubjects, myIds])

  const totals = useMemo(() => {
    return completions.reduce<Record<string, { papers: number; points: number }>>((acc, c) => {
      const current = acc[c.subjectId] ?? { papers: 0, points: 0 }
      return { ...acc, [c.subjectId]: { papers: current.papers + 1, points: current.points + completionPoints(c.percentage, c.timed) } }
    }, {})
  }, [completions])

  const handleAdd = async (subject: SubjectOption) => {
    setMessage(null)
    const result = await addSubject(supabase, userId, subject.id)
    if (!result.ok) {
      setMessage("That subject could not be added. Please try again.")
      return
    }
    setMyIds(ids => (ids.includes(subject.id) ? ids : [...ids, subject.id]))
    setSelectedId(subject.id)
    setQuery("")
    const counts = await countPapers(supabase, [subject.id])
    setPaperCounts(current => ({ ...current, ...counts }))
    router.refresh()
  }

  const handleRemove = async (subject: SubjectOption) => {
    setMessage(null)
    const result = await removeSubject(supabase, userId, subject.id)
    if (!result.ok) {
      setMessage("That subject could not be removed. Please try again.")
      return
    }
    const remaining = myIds.filter(id => id !== subject.id)
    setMyIds(remaining)
    setSelectedId(current => (current === subject.id ? remaining[0] ?? null : current))
    router.refresh()
  }

  /** A paper was ticked, updated or unticked: update local state, then the server-rendered rewards. */
  const handleCompletionsChange = useCallback((next: CompletionRecord[]) => {
    setCompletions(next)
    router.refresh()
  }, [router])

  const selected = mySubjects.find(s => s.id === selectedId) ?? null

  return (
    <section className="db-board" aria-labelledby="my-subjects-title">
      <div className="db-board-head">
        <div>
          <h2 id="my-subjects-title" className="db-title">My subjects</h2>
          <p className="db-muted">Add the subjects you are sitting, then tick off each paper you complete.</p>
        </div>
        <div className="db-add">
          <input
            type="search"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Add a subject — name or code"
            aria-label="Search for a subject to add"
            autoComplete="off"
          />
          {query.trim() !== "" ? (
            <ul className="db-add-list">
              {matches.length === 0 ? <li className="db-add-none">No subject matches. Try a code such as 4PH1 or WMA11.</li> : null}
              {matches.map(subject => (
                <li key={subject.id}>
                  <button type="button" onClick={() => handleAdd(subject)}>
                    <b>{subject.name}</b>
                    <span>{[subject.code, levelLabel(subject.level), subject.board].filter(Boolean).join(" · ")}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      {message ? <p className="db-alert" role="alert">{message}</p> : null}
      {!progressAvailable ? (
        <p className="db-notice">
          Saving completed papers and the leaderboards switch on once the dashboard database update is applied.
          You can add your subjects now.
        </p>
      ) : null}

      {loading ? (
        <p className="db-muted">Loading your subjects…</p>
      ) : mySubjects.length === 0 ? (
        <p className="db-empty">
          No subjects yet. Search above — for example “Physics”, “4MA1” or “Pure Mathematics 1” — and add each one you study.
        </p>
      ) : (
        <ul className="db-subjects">
          {mySubjects.map(subject => {
            const total = paperCounts[subject.id] ?? 0
            const done = totals[subject.id] ?? { papers: 0, points: 0 }
            const pct = total > 0 ? Math.min(100, Math.round((done.papers / total) * 100)) : 0
            return (
              <li key={subject.id} data-selected={subject.id === selectedId || undefined}>
                <button type="button" className="db-subject" onClick={() => setSelectedId(subject.id)} aria-pressed={subject.id === selectedId}>
                  <span className="db-code">{[subject.code, levelLabel(subject.level)].filter(Boolean).join(" · ")}</span>
                  <b>{subject.name}</b>
                  <span className="db-meter" aria-hidden><i style={{ width: `${pct}%` }} /></span>
                  <span className="db-subject-stats">
                    <span>{done.papers} / {total} papers</span>
                    <strong>{done.points} pts</strong>
                  </span>
                </button>
                <button type="button" className="db-remove" onClick={() => handleRemove(subject)} aria-label={`Remove ${subject.name} from my subjects`}>×</button>
              </li>
            )
          })}
        </ul>
      )}

      {selected ? (
        <div className="db-detail">
          <div className="db-tabs" role="tablist" aria-label={`${selected.name} sections`}>
            <button type="button" role="tab" aria-selected={tab === "papers"} onClick={() => setTab("papers")}>Papers</button>
            <button type="button" role="tab" aria-selected={tab === "leaderboard"} onClick={() => setTab("leaderboard")}>Leaderboard</button>
          </div>
          {tab === "papers" ? (
            <SubjectPapers
              key={selected.id}
              userId={userId}
              subject={selected}
              completions={completions}
              available={progressAvailable}
              onChange={handleCompletionsChange}
            />
          ) : (
            <SubjectLeaderboard key={selected.id} userId={userId} subject={selected} />
          )}
        </div>
      ) : null}
    </section>
  )
}
