import { createClient } from "@supabase/supabase-js"
import TestBuilderPage from "@/components/test-builder/TestBuilderPage"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export default async function TestBuilderRoute() {
  const supabase = createClient(supabaseUrl, supabaseKey)

  // Fetch subjects and first subject's topics in parallel on the server
  const { data: subjects } = await supabase
    .from("subjects")
    .select("id, name, code, level, board")
    .order("name")

  // IGCSE Edexcel subjects supported by the test builder pipeline.
  const ALLOWED_SUBJECT_CODES = [
    '4PH1', '4PH0',   // IGCSE Physics
    '4CH1', '4CH0',   // IGCSE Chemistry
    '4BI1', '4BI0',   // IGCSE Biology
    '4PM1',            // IGCSE Further Pure Mathematics
  ]
  const subjectList = (subjects || []).filter(s =>
    ALLOWED_SUBJECT_CODES.includes(s.code)
  )
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
