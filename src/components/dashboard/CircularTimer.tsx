"use client"
import { useEffect, useRef, useState } from "react"

function format(ms: number) {
  const m = Math.floor(ms / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

export default function CircularTimer() {
  const [targetMin, setTargetMin] = useState(90)   // default 90 minutes
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const raf = useRef<number | null>(null)
  const startedAt = useRef<number | null>(null)

  const radius = 70
  const circumference = 2 * Math.PI * radius
  const targetMs = Math.max(1, targetMin) * 60_000
  const progress = Math.min(1, elapsed / targetMs)
  const dash = `${circumference * progress} ${circumference}`

  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current) }, [])

  function tick(t: number) {
    if (startedAt.current == null) startedAt.current = t
  setElapsed(t - (startedAt.current as number))
    raf.current = requestAnimationFrame(tick)
  }

  function start() {
    if (running) return
    setElapsed(0)
    startedAt.current = null
    setRunning(true)
    raf.current = requestAnimationFrame(tick)
  }

  function stop() {
    if (raf.current) cancelAnimationFrame(raf.current)
    raf.current = null
    setRunning(false)
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4 flex flex-col items-center justify-center">
      <h2 className="text-lg font-semibold mb-3">Exam Timer</h2>

      <svg width="180" height="180" className="mb-3">
        <g transform="translate(90,90)">
          {/* track */}
          <circle r={radius} fill="none" stroke="rgba(255,255,255,.15)" strokeWidth="10" />
          {/* progress ring */}
          <circle
            r={radius}
            fill="none"
            stroke="rgb(16,185,129)" /* emerald-500 */
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={dash}
            transform="rotate(-90)"
          />
          {/* time text */}
          <text
            textAnchor="middle"
            dominantBaseline="central"
            fontSize="24"
            fill="#fff"
          >
            {format(elapsed)}
          </text>
        </g>
      </svg>

      <div className="flex items-center gap-3 mb-3">
        <label className="text-sm text-white/70">Target (min):</label>
        <input
          type="number"
          value={targetMin}
          onChange={(e) => setTargetMin(Math.max(1, Number(e.target.value)))}
          className="w-20 bg-black/30 rounded-md px-2 py-1 text-sm border border-white/10"
        />
      </div>

      <div className="flex gap-2">
        {!running ? (
          <button onClick={start} className="rounded-md bg-white text-black px-3 py-1.5 text-sm">Start</button>
        ) : (
          <button onClick={stop} className="rounded-md bg-emerald-500 text-white px-3 py-1.5 text-sm">Stop</button>
        )}
      </div>
    </section>
  )
}
