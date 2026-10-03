import { NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getUserQuestionLimit } from "@/lib/questionLimit"

// GET /api/tools/question-limit — the caller's per-paper question limit, so the
// worksheet generator and test builder can show it. Signed-out visitors get the
// normal-student limit. The generating routes enforce it independently.
export async function GET() {
  const { data: { user } } = await getSupabaseServer().auth.getUser()
  const { limit, proUntil } = await getUserQuestionLimit(user)
  return NextResponse.json(
    { limit, proUntil },
    { headers: { "Cache-Control": "private, no-store" } },
  )
}
