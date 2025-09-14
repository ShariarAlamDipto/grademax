"use client"
export type Row = { lecture_id: string; progress_percent: number }

export default function ProgressBars({ progressRows }: { progressRows: Row[] }) {
  // Very simple aggregate: average percent across all lectures (replace with per-subject grouping later)
  const avg = progressRows.length
    ? Math.round(progressRows.reduce((a, b) => a + (b.progress_percent || 0), 0) / progressRows.length)
    : 0

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="mb-2 text-sm text-white/70">Overall completion</div>
      <div className="h-3 w-full rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-white" style={{ width: `${avg}%` }} />
      </div>
      <div className="mt-2 text-sm text-white/80">{avg}% complete</div>
    </div>
  )
}
