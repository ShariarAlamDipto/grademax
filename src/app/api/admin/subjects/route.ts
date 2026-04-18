import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { logAdminAction } from "@/lib/auditLog"

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

  void logAdminAction({
    admin_email: auth.user?.email,
    action: "create_subject",
    entity_type: "subject",
    entity_id: data.id,
    details: { name, code: code || null, board: board || null, level },
  })

  return NextResponse.json({ success: true, subject: data })
}

// PATCH /api/admin/subjects — update a subject
export async function PATCH(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = adminDb()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const body = await req.json().catch(() => ({}))
  const { id, name, code, board, level, is_active } = body

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 })

  // Block name changes if the subject already has papers (renaming breaks all R2 paths)
  if (name !== undefined) {
    const { data: existing } = await db.from("subjects").select("name").eq("id", id).single()
    if (existing && existing.name !== name) {
      const { count } = await db.from("papers").select("id", { count: "exact", head: true }).eq("subject_id", id)
      if ((count ?? 0) > 0) {
        return NextResponse.json({
          error: `Cannot rename subject: ${count} paper(s) exist with R2 paths using the current name "${existing.name}". Rename would break all file paths.`,
        }, { status: 409 })
      }
    }
  }

  const updates: Record<string, string | boolean | null> = {}
  if (name !== undefined) updates.name = name
  if (code !== undefined) updates.code = code
  if (board !== undefined) updates.board = board
  if (level !== undefined) updates.level = level
  if (is_active !== undefined) updates.is_active = is_active

  const { data, error } = await db
    .from("subjects")
    .update(updates)
    .eq("id", id)
    .select("id, name, code, board, level")
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  void logAdminAction({
    admin_email: auth.user?.email,
    action: "update_subject",
    entity_type: "subject",
    entity_id: id,
    details: updates,
  })

  return NextResponse.json({ success: true, subject: data })
}

// DELETE /api/admin/subjects — delete a subject (and its papers cascade)
// Add ?preview=true to get impact counts without actually deleting.
export async function DELETE(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = adminDb()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const { searchParams } = new URL(req.url)
  const id = searchParams.get("id")
  const preview = searchParams.get("preview") === "true"

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 })

  // Always compute impact
  const { count: paperCount } = await db
    .from("papers")
    .select("id", { count: "exact", head: true })
    .eq("subject_id", id)

  if (preview) {
    return NextResponse.json({ paperCount: paperCount ?? 0 })
  }

  const { error } = await db.from("subjects").delete().eq("id", id)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  void logAdminAction({
    admin_email: auth.user?.email,
    action: "delete_subject",
    entity_type: "subject",
    entity_id: id,
    details: { deletedPaperCount: paperCount ?? 0 },
  })

  return NextResponse.json({ success: true, deletedPaperCount: paperCount ?? 0 })
}
