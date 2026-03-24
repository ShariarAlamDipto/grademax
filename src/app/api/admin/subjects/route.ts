import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

function adminDb() {
  const db = getSupabaseAdmin()
  if (!db) return null
  return db
}

// GET /api/admin/subjects — list all subjects with paper counts
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  // GET is read-only, allow fallback to session client if no service key
  const db = getSupabaseAdmin() || auth.db

  const { data: subjects, error } = await db
    .from("subjects")
    .select("id, name, code, board, level")
    .order("level", { ascending: true })
    .order("name", { ascending: true })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  // Get paper counts per subject (single query, one field)
  const { data: counts } = await db.from("papers").select("subject_id")

  const countMap = new Map<string, number>()
  for (const row of counts || []) {
    countMap.set(row.subject_id, (countMap.get(row.subject_id) || 0) + 1)
  }

  const result = (subjects || []).map(s => ({
    ...s,
    paperCount: countMap.get(s.id) || 0,
  }))

  return NextResponse.json({ subjects: result })
}

// POST /api/admin/subjects — create a new subject
export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = adminDb()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const body = await req.json().catch(() => ({}))
  const { name, code, board, level } = body

  if (!name || !level) {
    return NextResponse.json({ error: "name and level are required" }, { status: 400 })
  }

  const { data, error } = await db
    .from("subjects")
    .insert({ name, code: code || null, board: board || null, level })
    .select("id, name, code, board, level")
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ success: true, subject: data })
}

// PATCH /api/admin/subjects — update a subject
export async function PATCH(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = adminDb()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const body = await req.json().catch(() => ({}))
  const { id, name, code, board, level } = body

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 })

  const updates: Record<string, string | null> = {}
  if (name !== undefined) updates.name = name
  if (code !== undefined) updates.code = code
  if (board !== undefined) updates.board = board
  if (level !== undefined) updates.level = level

  const { data, error } = await db
    .from("subjects")
    .update(updates)
    .eq("id", id)
    .select("id, name, code, board, level")
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ success: true, subject: data })
}

// DELETE /api/admin/subjects — delete a subject (and its papers cascade)
export async function DELETE(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = adminDb()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const { searchParams } = new URL(req.url)
  const id = searchParams.get("id")

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 })

  const { error } = await db.from("subjects").delete().eq("id", id)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ success: true })
}
