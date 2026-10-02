import { unstable_cache } from "next/cache"
import { createClient } from "@supabase/supabase-js"

// Subjects offered by the worksheet generator (/generate) and the test builder
// (/test-builder). Each slot shows one subject; legacy code variants are
// listed as fallbacks.
export const TOOL_SUBJECT_SLOTS = [
  ['4PH1', '4PH0'],   // IGCSE Physics
  ['4MB1', '4MB0'],   // IGCSE Mathematics B
  ['4CH1', '4CH0'],   // IGCSE Chemistry
  ['4BI1', '4BI0'],   // IGCSE Biology
  ['4HB1', '4HB0'],   // IGCSE Human Biology
  ['4PM1', '9FM0'],   // IGCSE Further Pure Mathematics (9FM0 retained as legacy alias)
  ['WME01'],          // IAL Mechanics 1 (M1) -- NOT 4ME1, which is a separate IGCSE subject
  ['WST01'],          // IAL Statistics 1 (S1)
  ['WMA14'],          // IAL Pure Mathematics 4 (P4)
  ['WMA11'],          // IAL Pure Mathematics 1 (P1)
  ['WMA12'],          // IAL Pure Mathematics 2 (P2)
  ['WMA13'],          // IAL Pure Mathematics 3 (P3)
] as const

// Subjects and topics change only when a new subject is onboarded, so the
// lookup is cached instead of costing three Supabase round trips per visit.
const REVALIDATE_SECONDS = 3600

export type ToolSubject = { id: string; name: string; code: string; level: string; board: string }
export type ToolTopic = { id: string; code: string; name: string; description?: string }

async function loadToolSubjects(): Promise<{ subjects: ToolSubject[]; initialTopics: ToolTopic[] }> {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )

  const { data: rows, error } = await supabase
    .from("subjects")
    .select("id, name, code, level, board")
    .in("code", TOOL_SUBJECT_SLOTS.flat())
  // Throwing keeps a failed lookup out of the cache.
  if (error) throw new Error(`tool subjects lookup failed: ${error.message}`)

  const byCode = new Map((rows || []).map((s) => [String(s.code), s as ToolSubject]))

  // Paper counts only matter where a slot has more than one variant present.
  // A head count per subject avoids downloading every papers row (and the
  // 1000-row response cap that silently truncated the old tally).
  const ambiguousIds = TOOL_SUBJECT_SLOTS
    .map((codes) => codes.map((c) => byCode.get(c)).filter(Boolean) as ToolSubject[])
    .filter((candidates) => candidates.length > 1)
    .flat()
    .map((s) => s.id)
  const counts = await Promise.all(ambiguousIds.map(async (id) => {
    const { count } = await supabase
      .from("papers")
      .select("id", { count: "exact", head: true })
      .eq("subject_id", id)
    return [id, count || 0] as const
  }))
  const paperCount = new Map(counts)

  const subjects = TOOL_SUBJECT_SLOTS
    .map((codes) => {
      const candidates = codes.map((c) => byCode.get(c)).filter(Boolean) as ToolSubject[]
      // Prefer the variant that has real paper data; if tied, keep slot order.
      return [...candidates].sort((a, b) =>
        (paperCount.get(b.id) || 0) - (paperCount.get(a.id) || 0)
        || (codes as readonly string[]).indexOf(a.code) - (codes as readonly string[]).indexOf(b.code)
      )[0]
    })
    .filter((s): s is ToolSubject => Boolean(s))

  let initialTopics: ToolTopic[] = []
  if (subjects[0]) {
    const { data: topics } = await supabase
      .from("topics")
      .select("id, name, code, description")
      .eq("subject_id", subjects[0].id)
      .order("code")
    initialTopics = topics || []
  }

  return { subjects, initialTopics }
}

export const getToolSubjects = unstable_cache(loadToolSubjects, ["tool-subjects-v1"], {
  revalidate: REVALIDATE_SECONDS,
  tags: ["tool-subjects"],
})
