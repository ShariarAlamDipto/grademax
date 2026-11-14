// Page is implicitly dynamic due to cookies() usage in getSupabaseServer()

import type { Metadata } from "next"
import { redirect } from "next/navigation"

export const metadata: Metadata = {
  title: "Dashboard",
}
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"
import LevelAndGoal from "@/components/dashboard/LevelAndGoal"
import CircularTimer from "@/components/dashboard/CircularTimer"
import Link from "next/link"
import { RewardsPanel } from "@/components/rewards/RewardsPanel"
import { SubjectsBoard } from "@/components/dashboard/SubjectsBoard"
import "@/components/dashboard/dashboard-refresh.css"
import { loadRewards } from "@/lib/rewards/stats"

export default async function DashboardPage() {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect("/login")

  const displayName =
    (user.user_metadata?.full_name as string) ||
    (user.user_metadata?.name as string) ||
    user.email?.split("@")[0] ||
    "Student"

  // Step 1: Ensure the profile row exists
  const { error: profileError } = await supabase
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
    )
  if (profileError) console.error("[dashboard] profile upsert failed:", profileError.message)

  // Step 2: Auto-promote super admin AFTER profile guaranteed to exist
  if (isSuperAdmin(user.email)) {
    const admin = getSupabaseAdmin()
    if (admin) {
      await admin
        .from("profiles")
        .update({ role: "admin" })
        .eq("id", user.id)
    }
  }

  // Step 3: Fetch profile with up-to-date role, alongside the rewards counts
  const [{ data: profile }, rewards] = await Promise.all([
    supabase
      .from("profiles")
      .select("study_level, marks_goal_pct, role")
      .eq("id", user.id)
      .single(),
    loadRewards(supabase, user.id),
  ])

  const studyLevel = (profile?.study_level as "igcse" | "ial" | null) ?? null
  const marksGoal = profile?.marks_goal_pct ?? 90
  const userRole = (profile?.role as string) ?? "student"
  const showTeacherPanel = userRole === "teacher" || userRole === "admin" || isSuperAdmin(user.email)

  return (
    <main className="db-page">
      <div className="db-wrap">
        <header className="db-header">
          <div>
            <h1>Hi, {displayName}</h1>
            <p>Your subjects, completed papers, points and badges in one place.</p>
          </div>
          <div className="db-header-links">
            {showTeacherPanel && <Link href="/dashboard/teacher" className="db-btn">Teacher Panel</Link>}
            <Link href="/profile" className="db-btn">Edit Profile</Link>
          </div>
        </header>

        <div className="db-stack">
          <RewardsPanel data={rewards} />

          <div className="db-columns">
            <SubjectsBoard userId={user.id} />

            <aside className="db-side">
              <LevelAndGoal initialLevel={studyLevel} initialGoal={marksGoal} />
              <CircularTimer />
              <section className="db-panel">
                <h2>Quick access</h2>
                <div className="db-links">
                  <Link href="/generate">Worksheets<span>Generate topic practice</span></Link>
                  <Link href="/test-builder">Test Builder<span>Pick questions for a test</span></Link>
                  <Link href="/past-papers">Past papers<span>Question papers and mark schemes</span></Link>
                  <Link href="/lectures">Lectures<span>View lecture materials</span></Link>
                </div>
              </section>
            </aside>
          </div>
        </div>
      </div>
    </main>
  )
}
