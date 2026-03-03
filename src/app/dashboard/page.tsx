// Page is implicitly dynamic due to cookies() usage in getSupabaseServer()

import { redirect } from "next/navigation"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"
import LevelAndGoal from "@/components/dashboard/LevelAndGoal"
import SubjectDropdown from "@/components/dashboard/SubjectDropdown"
import PapersChecklist from "@/components/dashboard/PapersChecklist"
import CircularTimer from "@/components/dashboard/CircularTimer"
import LazyMarksChart from "@/components/dashboard/LazyMarksChart"
import Link from "next/link"

export default async function DashboardPage() {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect("/login")

  // Auto-promote super admin if needed
  if (isSuperAdmin(user.email)) {
    const admin = getSupabaseAdmin()
    if (admin) {
      await admin
        .from("profiles")
        .update({ role: "admin" })
        .eq("id", user.id)
    }
  }

  const displayName =
    (user.user_metadata?.full_name as string) ||
    (user.user_metadata?.name as string) ||
    user.email?.split("@")[0] ||
    "Student"

  // Run upsert and profile fetch in parallel where possible
  // Use upsert with select to combine two calls into one
  const [, { data: profile }, { data: userSubjects }] = await Promise.all([
    supabase
      .from("profiles")
      .upsert(
        {
          id: user.id,
          email: user.email,
          full_name:
            (user.user_metadata?.full_name as string) ||
            (user.user_metadata?.name as string) ||
            null,
          avatar_url: (user.user_metadata?.avatar_url as string) || null,
        },
        { onConflict: "id", ignoreDuplicates: true }
      ),
    supabase
      .from("profiles")
      .select("study_level, marks_goal_pct, role")
      .eq("id", user.id)
      .single(),
    supabase
      .from("user_subjects")
      .select("subject_id"),
  ])

  const studyLevel = (profile?.study_level as "igcse" | "ial" | null) ?? null
  const marksGoal = profile?.marks_goal_pct ?? 90
  const subjectIds = (userSubjects || []).map((r: { subject_id: string }) => r.subject_id)
  const userRole = (profile?.role as string) ?? "student"

  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      {/* Dashboard Header */}
      <div className="max-w-6xl mx-auto py-6 mb-2">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">Hi, {displayName} 👋</h1>
            <p className="text-sm text-white/50 mt-1">Welcome to your dashboard</p>
          </div>
          <div className="flex items-center gap-3">
            {(userRole === "teacher" || userRole === "admin") && (
              <Link
                href="/dashboard/teacher"
                className="rounded-lg border border-blue-400/30 bg-blue-400/10 px-4 py-2 text-sm text-blue-400 hover:bg-blue-400/20 transition-colors"
              >
                Teacher Panel
              </Link>
            )}
            <Link
              href="/profile"
              className="rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
            >
              Edit Profile
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto grid gap-8 md:grid-cols-3">
        {/* Left column: Level, Goal, Subjects */}
        <div className="md:col-span-1 space-y-6">
          <LevelAndGoal initialLevel={studyLevel} initialGoal={marksGoal} />
          <SubjectDropdown currentLevel={studyLevel} initialEnrolled={subjectIds} />
        </div>

        {/* Right column: Timer + Papers + Chart */}
        <div className="md:col-span-2 space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <CircularTimer />
            <LazyMarksChart firstSubjectId={subjectIds[0] || null} />
          </div>
          <PapersChecklist initialSubjectIds={subjectIds} marksGoal={marksGoal} userId={user.id} />

          {/* Quick Links */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h2 className="text-lg font-semibold mb-3">Quick Access</h2>
            <div className="grid gap-3 grid-cols-2">
              <Link
                href="/lectures"
                className="flex items-center gap-3 rounded-xl bg-white/5 border border-white/5 px-4 py-3 hover:bg-white/10 transition-colors"
              >
                <span className="text-2xl">📚</span>
                <div>
                  <p className="text-sm font-medium">Lectures</p>
                  <p className="text-xs text-white/40">View lecture materials</p>
                </div>
              </Link>
              <Link
                href="/generate"
                className="flex items-center gap-3 rounded-xl bg-white/5 border border-white/5 px-4 py-3 hover:bg-white/10 transition-colors"
              >
                <span className="text-2xl">📝</span>
                <div>
                  <p className="text-sm font-medium">Worksheets</p>
                  <p className="text-xs text-white/40">Generate practice sheets</p>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
