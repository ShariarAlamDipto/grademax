import { NextResponse } from "next/server"
import { z } from "zod"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getSupabaseServer } from "@/lib/supabaseServer"

export const dynamic = "force-dynamic"

const suggestionSchema = z.object({
  name: z.string().trim().max(120).optional().nullable(),
  email: z.string().trim().email().max(254).optional().nullable().or(z.literal("")),
  message: z.string().trim().min(5, "Message is too short").max(5000, "Message is too long"),
})

export async function POST(req: Request) {
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
    return NextResponse.json({ error: "Server misconfigured" }, { status: 500 })
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
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
