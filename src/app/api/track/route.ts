import { NextRequest, NextResponse } from "next/server"
import { requireAuth } from "@/lib/apiAuth"
import { trackUsage, UsageFeature } from "@/lib/trackUsage"

const VALID_FEATURES: UsageFeature[] = [
  "lecture_view",
  "lecture_download",
  "worksheet_generate",
  "worksheet_download",
  "test_builder_session",
  "test_builder_download",
]

export async function POST(req: NextRequest) {
  const auth = await requireAuth()
  if ("error" in auth) return auth.error

  const body = await req.json().catch(() => null)
  if (!body || !VALID_FEATURES.includes(body.feature)) {
    return NextResponse.json({ error: "Invalid event" }, { status: 400 })
  }

  await trackUsage({
    user_id: auth.user.id,
    feature: body.feature as UsageFeature,
    subject_id: body.subject_id ?? null,
    subject_name: body.subject_name ?? null,
    metadata: body.metadata ?? null,
  })

  return NextResponse.json({ ok: true })
}
