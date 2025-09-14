
import { redirect } from "next/navigation"
import { getSupabaseServer } from "@/lib/supabaseServer"
import LevelAndGoal from "@/components/dashboard/LevelAndGoal"
import SubjectDropdown from "@/components/dashboard/SubjectDropdown"
import PapersChecklist from "@/components/dashboard/PapersChecklist"
import CircularTimer from "@/components/dashboard/CircularTimer"
import MarksChart from "@/components/dashboard/MarksChart"
import AuthButton from "@/components/AuthButton"

export default async function DashboardPage() {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect("/login")

  const displayName =
    (user.user_metadata?.full_name as string) ||
    (user.user_metadata?.name as string) ||
    user.email?.split("@")[0] ||
    "Student"

  const { data: profile } = await supabase
    .from("profiles")
    .select("study_level, marks_goal_pct")
    .eq("id", user.id)
    .single()

  const studyLevel = (profile?.study_level as "igcse" | "ial" | null) ?? null
  const marksGoal = profile?.marks_goal_pct ?? 90

  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-black/60 backdrop-blur border-b border-white/10 -mx-6 px-6 py-4 mb-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-xl md:text-2xl font-semibold">Hi, {displayName} 👋</h1>
          <AuthButton />
        </div>
      </div>

      <div className="max-w-6xl mx-auto grid gap-8 md:grid-cols-3">
        {/* Left column: Level, Goal, Subjects */}
        <div className="md:col-span-1 space-y-6">
          <LevelAndGoal initialLevel={studyLevel} initialGoal={marksGoal} />
          <SubjectDropdown currentLevel={studyLevel} />
        </div>

        {/* Right column: Timer + Papers + Chart */}
        <div className="md:col-span-2 space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <CircularTimer />
            <MarksChart />
          </div>
          <PapersChecklist />
        </div>
      </div>
    </main>
  )
}
