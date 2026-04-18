import { createClient } from "@supabase/supabase-js"
import TestBuilderPage from "@/components/test-builder/TestBuilderPage"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export default async function TestBuilderRoute() {
  const supabase = createClient(supabaseUrl, supabaseKey)

  // Fetch subjects and first subject's topics in parallel on the server
  // IGCSE Edexcel subjects supported by the test builder pipeline.
  const TEST_BUILDER_SUBJECT_SLOTS = [
    ['4PH1', '4PH0'], // IGCSE Physics
    ['4MB1', '4MB0'], // IGCSE Mathematics B
    ['4CH1', '4CH0'], // IGCSE Chemistry
    ['4BI1', '4BI0'], // IGCSE Biology
    ['4PM1', '9FM0'], // IGCSE Further Pure Mathematics (9FM0 retained as legacy alias)
  ] as const

  const ALLOWED_SUBJECT_CODES = TEST_BUILDER_SUBJECT_SLOTS.flat()

  const { data: subjects } = await supabase
    .from("subjects")
    .select("id, name, code, level, board")
    .in("code", ALLOWED_SUBJECT_CODES)

  const subjectIds = (subjects || []).map((subject) => subject.id)
  const paperCountBySubjectId = new Map<string, number>()
  if (subjectIds.length > 0) {
    const { data: papers } = await supabase
      .from('papers')
      .select('subject_id')
      .in('subject_id', subjectIds)

    for (const paper of papers || []) {
      const key = String(paper.subject_id)
      paperCountBySubjectId.set(key, (paperCountBySubjectId.get(key) || 0) + 1)
    }
  }

  const subjectsByCode = new Map((subjects || []).map((subject) => [String(subject.code), subject]))

  const subjectList = TEST_BUILDER_SUBJECT_SLOTS
    .map((slotCodes) => {
      const candidates = slotCodes
        .map((code) => subjectsByCode.get(code))
        .filter((subject): subject is NonNullable<typeof subject> => Boolean(subject))

      if (candidates.length === 0) return undefined
      if (candidates.length === 1) return candidates[0]

      // Prefer the subject variant that has real paper data; if tied, keep slot order.
      return candidates.sort((a, b) => {
        const countDiff = (paperCountBySubjectId.get(String(b.id)) || 0) - (paperCountBySubjectId.get(String(a.id)) || 0)
        if (countDiff !== 0) return countDiff
        const slotOrder = slotCodes as readonly string[]
        return slotOrder.indexOf(String(a.code)) - slotOrder.indexOf(String(b.code))
      })[0]
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
    <TestBuilderPage
      initialSubjects={subjectList}
      initialTopics={initialTopics}
    />
  )
}
