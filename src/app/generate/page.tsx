import { createClient } from "@supabase/supabase-js"
import WorksheetGenerator from "@/components/generate/WorksheetGenerator"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Show one subject per slot and support legacy code variants when present.
const WORKSHEET_SUBJECT_SLOTS = [
  ['4MB1', '4MB0'],
  ['4PH1', '4PH0'],
  ['WMA11', '9FM0'],
  ['4CH1', '4CH0'],
  ['4BI1', '4BI0'],
] as const

const ALLOWED_WORKSHEET_SUBJECT_CODES = WORKSHEET_SUBJECT_SLOTS.flat()

export default async function GeneratePage() {
  const supabase = createClient(supabaseUrl, supabaseKey)

  // Fetch subjects and first subject's topics in parallel on the server
  const { data: subjects } = await supabase
    .from("subjects")
    .select("id, name, code, level, board")
    .in('code', [...ALLOWED_WORKSHEET_SUBJECT_CODES])

  const subjectsByCode = new Map((subjects || []).map((subject) => [String(subject.code), subject]))

  const subjectList = WORKSHEET_SUBJECT_SLOTS
    .map((slotCodes) => {
      for (const code of slotCodes) {
        const subject = subjectsByCode.get(code)
        if (subject) return subject
      }
      return undefined
    })
    .filter((subject): subject is NonNullable<typeof subject> => Boolean(subject))
  const firstSubjectId = subjectList[0]?.id

  let initialTopics: { id: string; code: string; name: string; description?: string }[] = []
  if (firstSubjectId) {
    const { data: topics } = await supabase
      .from("topics")
      .select("id, name, code, description")
      .eq("subject_id", firstSubjectId)
      .order("code")
    initialTopics = topics || []
  }

  return (
    <WorksheetGenerator
      initialSubjects={subjectList}
      initialTopics={initialTopics}
    />
  )
}
