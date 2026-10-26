import { NextRequest, NextResponse } from "next/server"
import { requireAuth } from "@/lib/apiAuth"
import { trackUsage, UsageFeature } from "@/lib/trackUsage"
import { trackServerEvent } from "@/lib/siteEvents"

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

  // The Test Builder assembles its PDFs in the browser, so this report is the
  // only point the server learns a test was made (Visitors → Tools & health).
  if (body.feature === "test_builder_download") {
    const subject = typeof body.subject_name === "string" ? body.subject_name.slice(0, 120) : null
    const count = Number(body.metadata?.question_count)
    const questions = Number.isFinite(count) && count >= 0 ? Math.min(Math.floor(count), 1000) : null
    await trackServerEvent("test_generated", "/test-builder", subject, {
      requested: questions, supplied: questions, partial: false, built_in_browser: true,
    })
  }

  return NextResponse.json({ ok: true })
}
