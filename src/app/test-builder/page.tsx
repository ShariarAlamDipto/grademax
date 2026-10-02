import { connection } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { isPublicToolsTrialActive } from "@/lib/publicToolsTrial"
import { getToolSubjects } from "@/lib/toolSubjects"
import TestBuilderPage from "@/components/test-builder/TestBuilderPage"
import TestBuilderLanding from "@/components/test-builder/TestBuilderLanding"

export default async function TestBuilderRoute() {
  // Render per request: the access gate depends on the current date, which a
  // prerendered page would freeze at build time.
  await connection()

  // Logged-out visitors (and crawlers) get the indexable landing page instead of
  // a 307 to /login — the tool itself still requires a session, except while the
  // free-access trial runs (see publicToolsTrial.ts). During the trial the
  // session is irrelevant, so the Supabase Auth round trip is skipped.
  if (!isPublicToolsTrialActive()) {
    const { data: { user } } = await getSupabaseServer().auth.getUser()
    if (!user) return <TestBuilderLanding />
  }

  const { subjects, initialTopics } = await getToolSubjects()

  return (
    <TestBuilderPage
      initialSubjects={subjects}
      initialTopics={initialTopics}
    />
  )
}
