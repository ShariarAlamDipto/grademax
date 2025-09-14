"use client"
import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabaseClient"

export default function LevelAndGoal({
  initialLevel,
  initialGoal,
}: { initialLevel: "igcse" | "ial" | null; initialGoal: number }) {
  const [level, setLevel] = useState<"igcse" | "ial" | "">(initialLevel ?? "");
  const [goal, setGoal] = useState<number>(initialGoal || 90)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return
    await supabase
      .from("profiles")
      .upsert({ id: user.id, study_level: level || null, marks_goal_pct: goal })
    setSaving(false)
  }

  useEffect(() => { /* optionally autosave */ }, [])

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h2 className="text-lg font-semibold mb-3">Your setup</h2>

      <div className="mb-4">
        <div className="text-sm text-white/70 mb-1">Exam level</div>
        <div className="flex gap-2">
          <button
            onClick={() => setLevel("igcse")}
            className={`px-3 py-1.5 rounded-md border text-sm ${
              level === "igcse" ? "bg-white text-black border-white/20" : "bg-white/10 text-white border-white/10"
            }`}
          >
            IGCSE
          </button>
          <button
            onClick={() => setLevel("ial")}
            className={`px-3 py-1.5 rounded-md border text-sm ${
              level === "ial" ? "bg-white text-black border-white/20" : "bg-white/10 text-white border-white/10"
            }`}
          >
            IAL
          </button>
        </div>
      </div>

      <div className="mb-4">
        <label className="text-sm text-white/70 mb-1 block">Marks goal (%)</label>
        <input
          type="number"
          value={goal}
          onChange={(e) => setGoal(Math.max(0, Math.min(100, Number(e.target.value))))}
          className="w-24 bg-black/30 rounded-md px-2 py-1 text-sm border border-white/10"
        />
      </div>

      <button
        onClick={save}
        disabled={!level || saving}
        className="rounded-md bg-white text-black px-3 py-1.5 text-sm disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </section>
  )
}
