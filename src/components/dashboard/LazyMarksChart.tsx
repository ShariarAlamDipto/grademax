"use client"
import dynamic from "next/dynamic"

const MarksChart = dynamic(() => import("@/components/dashboard/MarksChart"), {
  ssr: false,
  loading: () => (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="mb-2 text-sm text-white/70">Performance Over Time</div>
      <div className="h-64 animate-pulse rounded-lg bg-white/5" />
    </div>
  ),
})

export default function LazyMarksChart({ firstSubjectId }: { firstSubjectId: string | null }) {
  return <MarksChart firstSubjectId={firstSubjectId} />
}
