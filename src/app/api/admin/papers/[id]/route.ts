import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET, R2_PUBLIC_URL } from "@/lib/r2Client"
import { DeleteObjectCommand } from "@aws-sdk/client-s3"
import { parseR2Key } from "@/lib/r2FilenameParser"
import { logAdminAction } from "@/lib/auditLog"

export const dynamic = "force-dynamic"

/**
 * DELETE /api/admin/papers/[id]
 * Deletes a paper row from DB and optionally removes associated R2 objects.
 * Query params:
 *   ?deleteR2=true  — also delete QP + MS files from R2 (if urls are present)
 */
export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const { id } = await params
  if (!id) return NextResponse.json({ error: "Missing paper id" }, { status: 400 })

  const deleteR2 = req.nextUrl.searchParams.get("deleteR2") === "true"

  const db = getSupabaseAdmin() || auth.db

  // Fetch the paper row first to get R2 URLs
  const { data: paper, error: fetchErr } = await db
    .from("papers")
    .select("id, pdf_url, markscheme_pdf_url")
    .eq("id", id)
    .maybeSingle()

  if (fetchErr) return NextResponse.json({ error: fetchErr.message }, { status: 500 })
  if (!paper) return NextResponse.json({ error: "Paper not found" }, { status: 404 })

  // Optionally delete R2 objects
  if (deleteR2) {
    const r2 = getR2Client()
    const baseUrl = R2_PUBLIC_URL
    const toDelete: string[] = []

    for (const url of [paper.pdf_url, paper.markscheme_pdf_url]) {
      if (!url?.startsWith(baseUrl + "/")) continue
      const key = url.slice(baseUrl.length + 1)
      // Validate the extracted key parses as a known R2 filename before deleting
      if (key && parseR2Key(key)) {
        toDelete.push(key)
      } else {
        console.warn("[delete paper] Skipping R2 delete — key failed validation:", key)
      }
    }

    for (const key of toDelete) {
      try {
        await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: key }))
      } catch (e) {
        console.warn("[delete paper] R2 delete failed for key:", key, e)
        // Non-fatal — proceed to delete DB row
      }
    }
  }

  // Delete the DB row
  const { error: deleteErr } = await db.from("papers").delete().eq("id", id)
  if (deleteErr) return NextResponse.json({ error: deleteErr.message }, { status: 500 })

  void logAdminAction({
    admin_email: auth.user?.email,
    action: "delete_paper",
    entity_type: "paper",
    entity_id: id,
    details: { deleteR2 },
  })

  return NextResponse.json({ success: true, id })
}

/**
 * PATCH /api/admin/papers/[id]
 * Clears a single URL field (pdf_url or markscheme_pdf_url) from a paper row.
 * Body: { field: "pdf_url" | "markscheme_pdf_url", deleteR2?: boolean }
 */
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const { id } = await params
  if (!id) return NextResponse.json({ error: "Missing paper id" }, { status: 400 })

  const body = await req.json().catch(() => ({}))
  const field = body.field as "pdf_url" | "markscheme_pdf_url" | undefined
  if (!field || !["pdf_url", "markscheme_pdf_url"].includes(field)) {
    return NextResponse.json({ error: "field must be pdf_url or markscheme_pdf_url" }, { status: 400 })
  }

  const db = getSupabaseAdmin() || auth.db

  const { data: paper, error: fetchErr } = await db
    .from("papers")
    .select("id, pdf_url, markscheme_pdf_url")
    .eq("id", id)
    .maybeSingle()

  if (fetchErr) return NextResponse.json({ error: fetchErr.message }, { status: 500 })
  if (!paper) return NextResponse.json({ error: "Paper not found" }, { status: 404 })

  // Optionally delete the R2 object
  if (body.deleteR2 && paper[field]) {
    const baseUrl = R2_PUBLIC_URL
    const url = paper[field]!
    if (url.startsWith(baseUrl + "/")) {
      const key = url.slice(baseUrl.length + 1)
      if (key && parseR2Key(key)) {
        try {
          const r2 = getR2Client()
          await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: key }))
        } catch (e) {
          console.warn("[patch paper] R2 delete failed for key:", key, e)
        }
      } else {
        console.warn("[patch paper] Skipping R2 delete — key failed validation:", key)
      }
    }
  }

  const { error: updateErr } = await db
    .from("papers")
    .update({ [field]: null })
    .eq("id", id)

  if (updateErr) return NextResponse.json({ error: updateErr.message }, { status: 500 })

  return NextResponse.json({ success: true, id, cleared: field })
}
