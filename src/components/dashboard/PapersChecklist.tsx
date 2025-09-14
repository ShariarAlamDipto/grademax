"use client"
import { useEffect, useMemo, useState } from "react"
import { supabase } from "@/lib/supabaseClient"

type Paper = { id: string; year: number; session: string; paper_code: string; max_score: number }
type Attempt = { id: string; paper_id: string | null; subject_id: string; percentage: number | null; raw_score: number | null }

export default function PapersChecklist() {
  const [goal, setGoal] = useState(90)
  const [subjectIds, setSubjectIds] = useState<string[]>([])
  const [papers, setPapers] = useState<Paper[]>([])
  const [attempts, setAttempts] = useState<Attempt[]>([])
  const [loading, setLoading] = useState(true)

  // Load profile goal + user subjects
  useEffect(() => {
    async function init() {
      const [, prof, us] = await Promise.all([
        supabase.auth.getUser(),
        supabase.from("profiles").select("marks_goal_pct").maybeSingle(),
        supabase.from("user_subjects").select("subject_id"),
      ])
      setGoal(prof.data?.marks_goal_pct ?? 90)
      setSubjectIds((us.data || []).map(r => r.subject_id))
    }
    init()
  }, [])

  // Load papers & attempts for the first selected subject (expand later to tabs)
  useEffect(() => {
    async function load() {
      if (!subjectIds[0]) { setPapers([]); setAttempts([]); setLoading(false); return }
      setLoading(true)
      const sid = subjectIds[0]
      const [pc, pa] = await Promise.all([
        supabase.from("papers_catalog").select("id,year,session,paper_code,max_score").eq("subject_id", sid).order("year", { ascending: false }),
        supabase.from("paper_attempts").select("id, subject_id, percentage, raw_score").eq("subject_id", sid).order("created_at", { ascending: true }).limit(500),
      ])
      setPapers(pc.data || [])
      setAttempts(pa.data?.map(a => ({ ...a, paper_id: null })) || []) // (optional: link attempt->paper if you add a column)
      setLoading(false)
    }
    load()
  }, [subjectIds])

  const completedCount = attempts.filter(a => typeof a.percentage === "number").length
  const total = papers.length
  const completionPct = total ? Math.round((completedCount / total) * 100) : 0

  const avgPct = useMemo(() => {
    const vals = attempts.map(a => a.percentage).filter((x): x is number => typeof x === "number")
    if (!vals.length) return 0
    return Math.round(vals.reduce((a,b)=>a+b,0) / vals.length)
  }, [attempts])

  async function markComplete(paper: Paper, raw: number) {
    // Create a finished attempt (no timer) with the entered raw score
    const percent = Math.max(0, Math.min(100, (raw / (paper.max_score || 100)) * 100))
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return
    const { error } = await supabase.from("paper_attempts").insert({
      user_id: user.id,
      subject_id: subjectIds[0],
      year: paper.year,
      session: paper.session,
      paper_code: paper.paper_code,
      max_score: paper.max_score,
      raw_score: raw,
      percentage: percent,
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      duration_ms: 0,
    })
    if (!error) {
      // refresh attempts
      const pa = await supabase
        .from("paper_attempts")
        .select("id, subject_id, percentage, raw_score")
        .eq("subject_id", subjectIds[0])
        .order("created_at", { ascending: true })
      setAttempts(pa.data?.map(a => ({ ...a, paper_id: null })) || [])
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Papers</h2>
        <div className="text-sm text-white/70">
          {subjectIds[0] ? "Selected subject loaded" : "Select your subjects to begin"}
        </div>
      </div>

      {/* Completion progress */}
      <div className="mb-4">
        <div className="text-sm text-white/70 mb-1">Completion</div>
        <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
          <div className="h-full bg-white" style={{ width: `${completionPct}%` }} />
        </div>
        <div className="mt-1 text-xs text-white/60">{completedCount}/{total} papers • {completionPct}%</div>
      </div>

      {/* Goal progress */}
      <div className="mb-4">
        <div className="text-sm text-white/70 mb-1">Marks goal</div>
        <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden relative">
          <div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, avgPct)}%` }} />
          <div
            className="absolute inset-y-0 border-l border-emerald-400/70"
            style={{ left: `${goal}%` }}
            title={`Goal ${goal}%`}
          />
        </div>
        <div className="mt-1 text-xs text-white/60">Average {avgPct}% • Goal {goal}%</div>
      </div>

      {/* Papers list */}
      {loading ? (
        <p className="text-sm text-white/70">Loading papers…</p>
      ) : !subjectIds[0] ? (
        <p className="text-sm text-white/70">Pick at least one subject from “Your subjects”.</p>
      ) : papers.length === 0 ? (
        <p className="text-sm text-white/70">No papers seeded yet for this subject.</p>
      ) : (
        <div className="max-h-[420px] overflow-auto pr-1 space-y-2">
          {papers.map((p) => (
            <PaperRow key={p.id} paper={p} onComplete={markComplete} />
          ))}
        </div>
      )}
    </section>
  )
}

function PaperRow({ paper, onComplete }: { paper: Paper; onComplete: (p: Paper, raw: number) => void }) {
  const [checked, setChecked] = useState(false)
  const [raw, setRaw] = useState<number | "">("")

  return (
    <div className="flex items-center gap-3 rounded-md border border-white/10 bg-white/5 px-3 py-2">
      <input
        type="checkbox"
        className="accent-white"
        checked={checked}
        onChange={async (e) => {
          const on = e.target.checked
          setChecked(on)
          if (on) {
            const val = typeof raw === "number" ? raw : 0
            await onComplete(paper, val)
          }
        }}
        title="Mark completed"
      />
      <div className="flex-1">
        <div className="text-sm">
          {paper.year} • {paper.session} • <span className="font-mono">{paper.paper_code}</span>
        </div>
        <div className="text-xs text-white/60">Max {paper.max_score}</div>
      </div>
      <input
        type="number"
        placeholder="Score"
        className="w-20 bg-black/30 rounded-md px-2 py-1 text-sm border border-white/10"
        value={raw}
        onChange={(e) => setRaw(Math.max(0, Math.min(paper.max_score, Number(e.target.value))))}
      />
      <button
        onClick={async () => {
          setChecked(true)
          const val = typeof raw === "number" ? raw : 0
          await onComplete(paper, val)
        }}
        className="rounded-md bg-white/10 hover:bg-white/15 px-3 py-1.5 text-sm"
      >
        Save
      </button>
    </div>
  )
}
