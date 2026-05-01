import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export type UsageFeature =
  | "lecture_view"
  | "lecture_download"
  | "worksheet_generate"
  | "worksheet_download"
  | "test_builder_session"
  | "test_builder_download"

export interface UsageEvent {
  user_id?: string | null
  feature: UsageFeature
  subject_id?: string | null
  subject_name?: string | null
  metadata?: Record<string, unknown>
}

export async function trackUsage(event: UsageEvent): Promise<void> {
  try {
    const db = getSupabaseAdmin()
    if (!db) return
    await db.from("usage_events").insert({
      user_id: event.user_id ?? null,
      feature: event.feature,
      subject_id: event.subject_id ?? null,
      subject_name: event.subject_name ?? null,
      metadata: event.metadata ?? null,
    })
  } catch {
    // Non-fatal — never break user-facing flows
  }
}
