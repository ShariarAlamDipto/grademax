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

  // Only expose subjects available in the test builder
  const ALLOWED_SUBJECTS = ['maths b', 'physics', 'further pure mathematics', 'biology', 'chemistry']
  const subjectList = (subjects || []).filter(s =>
    ALLOWED_SUBJECTS.some(allowed => s.name.toLowerCase().includes(allowed))
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
