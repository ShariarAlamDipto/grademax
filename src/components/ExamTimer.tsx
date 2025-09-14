"use client"
import { useEffect, useRef, useState } from "react"

type ExamTimerProps = {
  subjectId: string | null
}

export default function ExamTimer({ subjectId }: ExamTimerProps) {
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [ms, setMs] = useState(0)
  const tick = useRef<number | null>(null)
  const [year, setYear] = useState<number>(2025)
  const [session, setSession] = useState<string>("Jun")
  const [paperCode, setPaperCode] = useState<string>("P1")
  const [score, setScore] = useState<number>(0)

  useEffect(() => {
    return () => { if (tick.current) cancelAnimationFrame(tick.current) }
  }, [])

  function loop(last: number) {
    const now = performance.now()
    setMs(prev => prev + (now - last))
    tick.current = requestAnimationFrame(() => loop(now))
  }

  async function start() {
    if (!subjectId) {
      alert("Please select a subject before starting the timer.")
      return
    }
    const res = await fetch("/api/attempts/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject_id: subjectId, year, session, paper_code: paperCode, max_score: 100 }),
    })
    const json = await res.json()
    if (!json.ok) { alert("Failed to start attempt"); return }
    setAttemptId(json.attempt.id)
    setRunning(true)
    setMs(0)
    tick.current = requestAnimationFrame((t) => loop(t))
  }

  async function stop() {
    if (!attemptId) return
    if (tick.current) cancelAnimationFrame(tick.current)
    setRunning(false)
    try {
      await fetch("/api/attempts/finish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: attemptId, raw_score: score }),
      })
      alert("Attempt saved!")
    } catch {
      alert("Failed to save attempt")
    }
    setAttemptId(null)
  }

  const minutes = Math.floor(ms / 60000)
  const seconds = Math.floor((ms % 60000) / 1000).toString().padStart(2, "0")

  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 to-black/30 p-6 shadow-lg max-w-md mx-auto">
      <div className="mb-4 text-base font-semibold text-white/80 flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        Exam Timer
      </div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <input value={subjectId || ""} readOnly placeholder="Subject ID"
          className="bg-black/30 rounded-md px-3 py-2 text-sm border border-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/40"/>
        <input value={year} onChange={e=>setYear(Number(e.target.value))} placeholder="Year"
          className="bg-black/30 rounded-md px-3 py-2 text-sm border border-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/40"/>
        <input value={session} onChange={e=>setSession(e.target.value)} placeholder="Session"
          className="bg-black/30 rounded-md px-3 py-2 text-sm border border-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/40"/>
        <input value={paperCode} onChange={e=>setPaperCode(e.target.value)} placeholder="Paper Code"
          className="bg-black/30 rounded-md px-3 py-2 text-sm border border-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/40"/>
      </div>
      <div className="text-5xl font-bold mb-4 tabular-nums tracking-widest text-center text-white drop-shadow">
        {minutes}:{seconds}
      </div>
      <div className="flex gap-3 mb-4 justify-center">
        {!running ? (
          <button onClick={start} className="rounded-full bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-2 text-base font-semibold shadow hover:scale-105 active:scale-95 transition">Start</button>
        ) : (
          <button onClick={stop} className="rounded-full bg-red-500 text-white px-6 py-2 text-base font-semibold shadow hover:scale-105 active:scale-95 transition">Stop & Save</button>
        )}
      </div>
      <div className="flex items-center gap-2 justify-center">
        <label className="text-sm text-white/80">Your score:</label>
        <input type="number" value={score} onChange={e=>setScore(Number(e.target.value))}
          className="bg-black/30 rounded-md px-3 py-2 text-sm border border-white/10 w-24 focus:outline-none focus:ring-2 focus:ring-blue-400/40"/>
      </div>
    </div>
  )
}
