import { NextResponse } from "next/server"
import { z } from "zod"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

const ALLOWED_STATUS = ["new", "reviewed", "in_progress", "done", "archived"] as const

export async function GET(req: Request) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const { searchParams } = new URL(req.url)
  const status = searchParams.get("status")
  const limit = Math.min(Number(searchParams.get("limit") ?? 200), 500)

  let query = db
    .from("suggestions")
    .select("id, user_id, name, email, message, status, admin_notes, created_at, updated_at")
    .order("created_at", { ascending: false })
    .limit(limit)

  if (status && (ALLOWED_STATUS as readonly string[]).includes(status)) {
    query = query.eq("status", status)
  }

  const { data, error } = await query
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ suggestions: data ?? [] })
}

const updateSchema = z.object({
  id: z.string().uuid(),
  status: z.enum(ALLOWED_STATUS).optional(),
  admin_notes: z.string().max(5000).optional().nullable(),
})

export async function PATCH(req: Request) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const parsed = updateSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.issues[0]?.message ?? "Invalid input" }, { status: 400 })
  }

  const db = getSupabaseAdmin() || auth.db
  const { id, ...patch } = parsed.data

  if (Object.keys(patch).length === 0) {
    return NextResponse.json({ error: "No fields to update" }, { status: 400 })
  }

  const { error } = await db.from("suggestions").update(patch).eq("id", id)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ ok: true })
}

export async function DELETE(req: Request) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const { searchParams } = new URL(req.url)
  const id = searchParams.get("id")
  if (!id) return NextResponse.json({ error: "Missing id" }, { status: 400 })

  const db = getSupabaseAdmin() || auth.db
  const { error } = await db.from("suggestions").delete().eq("id", id)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ ok: true })
}
