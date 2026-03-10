
"use client"

import Link from "next/link"
import {
  pastPaperSubjects,
  subjectColorClasses,
  type Subject,
} from "@/lib/subjects"

const colorAccents: Record<Subject["colorKey"], string> = {
  physics:   "border-orange-400/30 hover:border-orange-400/60",
  maths:     "border-sky-400/30 hover:border-sky-400/60",
  biology:   "border-emerald-400/30 hover:border-emerald-400/60",
  chemistry: "border-violet-400/30 hover:border-violet-400/60",
  ict:       "border-red-400/30 hover:border-red-400/60",
  english:   "border-rose-400/30 hover:border-rose-400/60",
  other:     "border-indigo-400/30 hover:border-indigo-400/60",
}

function SubjectCard({ subject }: { subject: Subject }) {
  const accent = colorAccents[subject.colorKey]
  const badge = subjectColorClasses[subject.colorKey]

  return (
    <Link href={`/past-papers/${subject.slug}`}>
      <div
        className={`group relative bg-white/[0.03] border rounded-xl p-5
                    transition-all duration-300 hover:bg-white/[0.06] hover:scale-[1.02]
                    hover:shadow-lg hover:shadow-black/20 ${accent}`}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-white text-base group-hover:text-white/90 transition-colors">
              {subject.name}
            </h3>
            <span
              className={`inline-block mt-1.5 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${badge}`}
            >
              Edexcel {subject.level === "ial" ? "A Level" : "IGCSE"}
            </span>
          </div>
          <span className="text-white/20 group-hover:text-white/40 transition-colors text-lg">
            →
          </span>
        </div>
      </div>
    </Link>
  )
}

export default function PastPapersPage() {
  const igcse = pastPaperSubjects.filter((s) => s.level === "igcse")
  const ial = pastPaperSubjects.filter((s) => s.level === "ial")

  return (
    <main className="min-h-screen bg-black text-white px-6 py-12">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold mb-3">Past Papers</h1>
          <p className="text-white/50 max-w-lg mx-auto">
            Free Edexcel IGCSE &amp; A Level past papers with mark schemes.
            Download question papers organized by year and session.
          </p>
        </div>

        {/* IGCSE */}
        <section className="mb-12">
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-2xl font-bold">IGCSE</h2>
            <span className="text-xs text-white/30 font-medium bg-white/5 px-2.5 py-1 rounded-full">
              {igcse.length} subjects
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {igcse.map((s) => (
              <SubjectCard key={s.slug} subject={s} />
            ))}
          </div>
        </section>

        {/* IAL */}
        {ial.length > 0 && (
          <section>
            <div className="flex items-center gap-3 mb-6">
              <h2 className="text-2xl font-bold">A Level (IAL)</h2>
              <span className="text-xs text-white/30 font-medium bg-white/5 px-2.5 py-1 rounded-full">
                {ial.length} subjects
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {ial.map((s) => (
                <SubjectCard key={s.slug} subject={s} />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  )
}
