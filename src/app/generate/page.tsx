import { redirect } from "next/navigation"
import { connection } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { isPublicToolsTrialActive } from "@/lib/publicToolsTrial"
import { getToolSubjects } from "@/lib/toolSubjects"
import WorksheetGenerator from "@/components/generate/WorksheetGenerator"

export default async function GeneratePage() {
  // Render per request: the access gate depends on the current date, which a
  // prerendered page would freeze at build time.
  await connection()

  // While the tools are public the session is irrelevant here, so skip the
  // Supabase Auth round trip; otherwise run it alongside the data load.
  const userPromise = isPublicToolsTrialActive()
    ? Promise.resolve(null)
    : getSupabaseServer().auth.getUser().then(({ data }) => data.user)

  const [user, { subjects, initialTopics }] = await Promise.all([userPromise, getToolSubjects()])
  if (!user && !isPublicToolsTrialActive()) redirect("/login?next=/generate")

  return (
    <WorksheetGenerator
      initialSubjects={subjects}
      initialTopics={initialTopics}
    />
  )
}
