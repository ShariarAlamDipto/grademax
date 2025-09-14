"use client"
import { useEffect, useMemo, useState } from "react"
import { supabase } from "@/lib/supabaseClient"

export default function SubjectDropdown({ currentLevel }: { currentLevel: "igcse" | "ial" | null }) {
  const [open, setOpen] = useState(false)
  const [all, setAll] = useState<{ id: string; name: string; level: string }[]>([])
  const [enrolled, setEnrolled] = useState<Set<string>>(new Set())

  useEffect(() => {
    supabase.from("subjects").select("id,name,level").then(({ data }) => setAll(data || []))
    supabase.from("user_subjects").select("subject_id").then(({ data }) => {
      setEnrolled(new Set((data || []).map((r) => r.subject_id)))
    })
  }, [])

  const list = useMemo(
    () => all.filter((s) => (currentLevel ? s.level === currentLevel : true)),
    [all, currentLevel]
  )

  async function toggle(id: string, on: boolean) {
    if (on) {
      await supabase.from("user_subjects").insert({ subject_id: id })
      setEnrolled((prev) => new Set(prev).add(id))
    } else {
      await supabase.from("user_subjects").delete().eq("subject_id", id)
      setEnrolled((prev) => {
        const copy = new Set(prev)
        copy.delete(id)
        return copy
      })
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Your subjects</h2>
        <button
          onClick={() => setOpen((v) => !v)}
          className="text-sm text-white/70 underline underline-offset-4"
        >
          {open ? "Hide" : "Manage"}
        </button>
      </div>

      {open && (
        <div className="mt-4 max-h-64 overflow-auto space-y-2 pr-1">
          {list.map((s) => {
            const on = enrolled.has(s.id)
            return (
              <label key={s.id} className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="accent-white"
                  checked={on}
                  onChange={(e) => toggle(s.id, e.target.checked)}
                />
                <span>{s.name}</span>
              </label>
            )
          })}
        </div>
      )}

      {!open && (
        <p className="mt-2 text-sm text-white/70">
          {currentLevel ? `Showing ${currentLevel.toUpperCase()} subjects.` : "Pick your exam level to filter subjects."}
        </p>
      )}
    </section>
  )
}
