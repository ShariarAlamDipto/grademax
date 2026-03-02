import { createClient } from "@supabase/supabase-js"
import WorksheetGenerator from "@/components/generate/WorksheetGenerator"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export default async function GeneratePage() {
  const supabase = createClient(supabaseUrl, supabaseKey)

  // Fetch subjects and first subject's topics in parallel on the server
  const { data: subjects } = await supabase
    .from("subjects")
    .select("id, name, code, level, board")
    .order("name")

  const subjectList = subjects || []
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
