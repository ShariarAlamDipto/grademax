"use client"
import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabaseClient"

export type Row = { subject_id: string; subjects?: { name: string; slug: string } }


type SubjectPickerProps = {
  initial: Row[];
  onSelect?: (id: string | null) => void;
  selected?: string | null;
};

export default function SubjectPicker({ initial, onSelect, selected }: SubjectPickerProps) {
  const [rows, setRows] = useState<Row[]>(initial)
  const [allSubs, setAllSubs] = useState<{ id: string; name: string; slug: string; level: string }[]>([])

  useEffect(() => {
    supabase.from("subjects").select("id,name,slug,level").then(({ data }) => setAllSubs(data || []))
  }, [])

  const enrolledIds = new Set(rows.map(r => r.subject_id))

  async function toggle(id: string) {
    if (enrolledIds.has(id)) {
      await supabase.from("user_subjects").delete().eq("subject_id", id)
      setRows(prev => prev.filter(r => r.subject_id !== id))
      if (onSelect && selected === id) onSelect(null)
    } else {
      await supabase.from("user_subjects").insert({ subject_id: id })
      const s = allSubs.find(s => s.id === id)
      setRows(prev => [...prev, { subject_id: id, subjects: s ? { name: s.name, slug: s.slug } : undefined }])
      if (onSelect) onSelect(id)
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="flex flex-wrap gap-2">
        {allSubs.map(s => {
          const on = enrolledIds.has(s.id)
          const isSelected = selected === s.id
          return (
            <button
              key={s.id}
              onClick={() => {
                toggle(s.id)
                if (onSelect) onSelect(s.id)
              }}
              className={`px-3 py-1.5 rounded-md text-sm border transition
                ${isSelected ? "bg-blue-500 text-white border-blue-400" : on ? "bg-white text-black border-white/20" : "bg-white/10 text-white border-white/10 hover:bg-white/15"}`}
            >
              {s.name}
            </button>
          )
        })}
      </div>
    </div>
  )
}
