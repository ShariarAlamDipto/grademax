import { NextResponse } from "next/server"
import { z } from "zod"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { checkRateLimitByIp } from "@/lib/store/rateLimit"

const SAVE_FAILED = "We couldn't save your suggestion. Please try again in a moment."

export const dynamic = "force-dynamic"

const suggestionSchema = z.object({
  name: z.string().trim().max(120).optional().nullable(),
  email: z.string().trim().email().max(254).optional().nullable().or(z.literal("")),
  message: z.string().trim().min(5, "Message is too short").max(5000, "Message is too long"),
})

export async function POST(req: Request) {
  // Anyone can post here, so cap it per IP before reading the body.
  if (!(await checkRateLimitByIp("suggestion"))) {
    return NextResponse.json(
      { error: "You've sent several suggestions in a short time. Please wait a few minutes and try again." },
      { status: 429 }
    )
  }

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const parsed = suggestionSchema.safeParse(body)
  if (!parsed.success) {
    const issue = parsed.error.issues[0]
    return NextResponse.json({ error: issue?.message ?? "Invalid input" }, { status: 400 })
  }

  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()

  const db = getSupabaseAdmin()
  if (!db) {
    console.error("[suggestions] Supabase admin client is not configured")
    return NextResponse.json({ error: SAVE_FAILED }, { status: 500 })
  }

  const emailValue = parsed.data.email && parsed.data.email !== "" ? parsed.data.email : user?.email ?? null
  const nameValue = parsed.data.name && parsed.data.name !== "" ? parsed.data.name : null

  const { error } = await db.from("suggestions").insert({
    user_id: user?.id ?? null,
    name: nameValue,
    email: emailValue,
    message: parsed.data.message,
  })

  if (error) {
    // Database details stay in the server log; the visitor gets a plain message.
    console.error(`[suggestions] insert failed (${error.code ?? "no code"}): ${error.message}`)
    return NextResponse.json({ error: SAVE_FAILED }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
