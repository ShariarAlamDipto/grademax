"use client"

import { useEffect, useMemo, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import {
  listPapers, removeCompletion, saveCompletion,
  type CompletionRecord, type PaperOption, type SubjectOption,
} from "@/lib/dashboard/studentData"
import { completionPoints, percentageOf } from "@/lib/rewards/points"
import { seasonDisplay } from "@/lib/subjects"

/**
 * The paper checklist for one subject. Ticking "Completed" saves the paper and
 * earns 20 points; adding a score and marking it as timed earns more.
 */

interface SubjectPapersProps {
  userId: string
  subject: SubjectOption
  /** Every completion of this student (all subjects). */
  completions: CompletionRecord[]
  /** false while the completions table does not exist yet. */
  available: boolean
  onChange: (next: CompletionRecord[]) => void
}

/** Years shown before "Show older years" is pressed. */
const YEARS_SHOWN = 4

/** "" -> null; otherwise a non-negative number, or undefined when it is not a valid number. */
function parseScore(raw: string): number | null | undefined {
  const text = raw.trim()
  if (text === "") return null
  const value = Number(text)
  return Number.isFinite(value) && value >= 0 && value <= 1000 ? value : undefined
}

export function SubjectPapers({ userId, subject, completions, available, onChange }: SubjectPapersProps) {
  const [papers, setPapers] = useState<PaperOption[]>([])
  const [loading, setLoading] = useState(true)
  const [showAll, setShowAll] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listPapers(supabase, subject.id).then(result => {
      if (cancelled) return
      if (result.ok) setPapers(result.data)
      else setError("The paper list could not be loaded. Reload the page to try again.")
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [subject.id])

  const done = useMemo(() => new Map(completions.filter(c => c.subjectId === subject.id).map(c => [c.paperId, c])), [completions, subject.id])

  const years = useMemo(() => {
    const byYear = new Map<number, PaperOption[]>()
    for (const paper of papers) byYear.set(paper.year, [...(byYear.get(paper.year) ?? []), paper])
    return [...byYear.entries()].sort((a, b) => b[0] - a[0])
  }, [papers])

  const replace = (record: CompletionRecord) =>
    onChange([...completions.filter(c => c.paperId !== record.paperId), record])

  const save = async (paper: PaperOption, patch: { rawScore?: number | null; maxScore?: number | null; timed?: boolean }) => {
    const current = done.get(paper.id)
    setBusyId(paper.id)
    setError(null)
    const result = await saveCompletion(supabase, {
      userId,
      paperId: paper.id,
      subjectId: subject.id,
      rawScore: patch.rawScore !== undefined ? patch.rawScore : current?.rawScore ?? null,
      maxScore: patch.maxScore !== undefined ? patch.maxScore : current?.maxScore ?? null,
      timed: patch.timed !== undefined ? patch.timed : current?.timed ?? false,
    })
    setBusyId(null)
    if (result.ok) replace(result.data)
    else setError(result.unavailable ? "Saving switches on once the dashboard database update is applied." : "That could not be saved. Check the score is not above the maximum, then try again.")
  }

  const untick = async (paper: PaperOption) => {
    setBusyId(paper.id)
    setError(null)
    const result = await removeCompletion(supabase, userId, paper.id)
    setBusyId(null)
    if (result.ok) onChange(completions.filter(c => c.paperId !== paper.id))
    else setError("That could not be removed. Please try again.")
  }

  const saveScore = (paper: PaperOption, field: "rawScore" | "maxScore", raw: string) => {
    const value = parseScore(raw)
    if (value === undefined) {
      setError("Enter the score as a number, for example 54.")
      return
    }
    const current = done.get(paper.id)
    if ((current?.[field] ?? null) === value) return
    void save(paper, { [field]: value })
  }

  if (loading) return <p className="db-muted">Loading papers…</p>
  if (papers.length === 0) return <p className="db-empty">{error ?? `No past papers are listed for ${subject.name} yet.`}</p>

  const visibleYears = showAll ? years : years.slice(0, YEARS_SHOWN)

  return (
    <div>
      <p className="db-muted db-rules">
        Each completed paper earns <b>20 points</b>, plus up to <b>30</b> for your score and <b>5</b> if you sat it timed.
      </p>
      {error ? <p className="db-alert" role="alert">{error}</p> : null}

      {visibleYears.map(([year, list]) => (
        <section key={year} className="db-year" aria-label={`${year} papers`}>
          <h3>{year}<span>{list.filter(p => done.has(p.id)).length} / {list.length} done</span></h3>
          <ul>
            {list.map(paper => {
              const record = done.get(paper.id)
              const checkboxId = `done-${paper.id}`
              const percentage = record ? record.percentage ?? percentageOf(record.rawScore, record.maxScore) : null
              return (
                <li key={paper.id} data-done={record ? "" : undefined}>
                  <label htmlFor={checkboxId} className="db-check">
                    <input
                      id={checkboxId}
                      type="checkbox"
                      checked={Boolean(record)}
                      disabled={!available || busyId === paper.id}
                      onChange={e => (e.target.checked ? save(paper, {}) : untick(paper))}
                    />
                    <span>{seasonDisplay(paper.season)} · Paper {paper.paperNumber || "—"}</span>
                  </label>

                  {record ? (
                    <div className="db-score">
                      <input
                        type="text" inputMode="decimal" aria-label="Your score" placeholder="Score"
                        defaultValue={record.rawScore ?? ""} key={`raw-${record.rawScore}`}
                        onBlur={e => saveScore(paper, "rawScore", e.target.value)}
                      />
                      <span aria-hidden>/</span>
                      <input
                        type="text" inputMode="decimal" aria-label="Maximum marks" placeholder="Out of"
                        defaultValue={record.maxScore ?? ""} key={`max-${record.maxScore}`}
                        onBlur={e => saveScore(paper, "maxScore", e.target.value)}
                      />
                      <label className="db-timed">
                        <input type="checkbox" checked={record.timed} disabled={busyId === paper.id} onChange={e => save(paper, { timed: e.target.checked })} />
                        Timed
                      </label>
                      {percentage !== null ? <span className="db-pct">{Math.round(percentage)}%</span> : null}
                      <strong className="db-points">+{completionPoints(percentage, record.timed)} pts</strong>
                    </div>
                  ) : null}
                </li>
              )
            })}
          </ul>
        </section>
      ))}

      {years.length > YEARS_SHOWN ? (
        <button type="button" className="db-more" onClick={() => setShowAll(v => !v)}>
          {showAll ? "Show recent years only" : `Show older years (${years.length - YEARS_SHOWN} more)`}
        </button>
      ) : null}
    </div>
  )
}
