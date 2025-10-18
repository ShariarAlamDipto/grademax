export const dynamic = "force-dynamic"

import { redirect } from "next/navigation"
import { getSupabaseServer } from "@/lib/supabaseServer"
import LevelAndGoal from "@/components/dashboard/LevelAndGoal"
import SubjectDropdown from "@/components/dashboard/SubjectDropdown"
import PapersChecklist from "@/components/dashboard/PapersChecklist"
import CircularTimer from "@/components/dashboard/CircularTimer"
import MarksChart from "@/components/dashboard/MarksChart"
import AuthButton from "@/components/AuthButton"
import Link from "next/link"

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

  // Get user permissions and usage stats (Phase 1 features)
  // Gracefully handle if Phase 1 migration not applied yet
  let permissions = null;
  let usageData = null;
  let hasPermission = false;
  let maxWorksheetsPerMonth = null;
  let worksheetPercentage = 0;
  
  try {
    const permResult = await supabase
      .from('user_permissions')
      .select('can_generate_worksheets, is_active, max_worksheets_per_day, max_questions_per_worksheet')
      .eq('user_id', user.id)
      .single();
    permissions = permResult.data;
    
    // Get usage stats for current month (only if function exists)
    try {
      const usageResult = await supabase
        .rpc('get_current_month_usage', { check_user_id: user.id });
      usageData = usageResult.data;
    } catch {
      // Function doesn't exist yet (migration not applied)
      console.log('Phase 1 migration not applied yet - usage tracking disabled');
    }
    
    hasPermission = (permissions?.can_generate_worksheets && permissions?.is_active) || false;
    maxWorksheetsPerMonth = permissions?.max_worksheets_per_day 
      ? permissions.max_worksheets_per_day * 30 
      : null;
  } catch {
    // Phase 1 tables don't exist yet
    console.log('Phase 1 tables not found - using legacy auth');
  }

  const usage = usageData || { worksheets_generated: 0, pages_generated: 0, questions_generated: 0 };
  worksheetPercentage = maxWorksheetsPerMonth 
    ? Math.round((usage.worksheets_generated / maxWorksheetsPerMonth) * 100)
    : 0;

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
        {/* Phase 1: Usage Stats Banner */}
        {usage.worksheets_generated > 0 && (
          <div className="md:col-span-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-lg p-4">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-6">
                <div>
                  <p className="text-sm text-gray-400">Worksheets This Month</p>
                  <p className="text-2xl font-bold text-white">
                    {usage.worksheets_generated}
                    {maxWorksheetsPerMonth && <span className="text-gray-400 text-base"> / {maxWorksheetsPerMonth}</span>}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Pages Generated</p>
                  <p className="text-2xl font-bold text-white">{usage.pages_generated}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Questions Practiced</p>
                  <p className="text-2xl font-bold text-white">{usage.questions_generated}</p>
                </div>
              </div>
              <Link
                href="/generate"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Generate More
              </Link>
            </div>
            {maxWorksheetsPerMonth && (
              <div className="mt-3">
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all ${
                      worksheetPercentage >= 90 ? 'bg-red-500' :
                      worksheetPercentage >= 70 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(worksheetPercentage, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">{worksheetPercentage}% of monthly quota used</p>
              </div>
            )}
          </div>
        )}

        {/* Permission Alert */}
        {!hasPermission && (
          <div className="md:col-span-3 bg-yellow-600/20 border border-yellow-500/30 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⏳</span>
              <div>
                <p className="text-white font-medium">Worksheet Generation Pending</p>
                <p className="text-sm text-gray-400">Your account is awaiting admin approval for worksheet generation access</p>
              </div>
            </div>
          </div>
        )}

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
