import type { User } from "@supabase/supabase-js"
import { getSupabaseAdmin, isSuperAdmin } from "./supabaseAdmin"
import { MAX_QUESTIONS_PER_PAPER, questionLimitFor, type QuestionLimit } from "./toolLimits"

export interface UserLimit {
  limit: QuestionLimit
  role: string
  proUntil: string | null
}

const CAPPED: UserLimit = { limit: MAX_QUESTIONS_PER_PAPER, role: "student", proUntil: null }

// Reads the role and Pro expiry with the service client, so a user can never
// widen their own limit. Any failure falls back to the normal-student limit.
export async function getUserQuestionLimit(user: User | null): Promise<UserLimit> {
  if (!user) return CAPPED
  if (isSuperAdmin(user.email)) return { limit: null, role: "admin", proUntil: null }

  const admin = getSupabaseAdmin()
  if (!admin) {
    console.error("[questionLimit] service client unavailable; applying the student limit")
    return CAPPED
  }

  const { data, error } = await admin
    .from("profiles")
    .select("role, pro_until")
    .eq("id", user.id)
    .maybeSingle()

  if (error) {
    // Before migration 32 is applied pro_until does not exist; roles still count.
    console.error("[questionLimit] profile lookup failed:", error.message)
    const { data: roleRow } = await admin.from("profiles").select("role").eq("id", user.id).maybeSingle()
    const role = roleRow?.role || "student"
    return { limit: questionLimitFor({ role }), role, proUntil: null }
  }

  const role = data?.role || "student"
  const proUntil = data?.pro_until ?? null
  return { limit: questionLimitFor({ role, proUntil }), role, proUntil }
}
