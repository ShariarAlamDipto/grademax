import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { logAdminAction } from "@/lib/auditLog"
import { PRO_PACK_DAYS } from "@/lib/toolLimits"

const DAY_MS = 24 * 60 * 60 * 1000
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

// POST /api/admin/users/pro — grant or revoke a Pro Student Pack (admin only).
// Body: { userId, action: "grant" | "revoke" }. A grant runs PRO_PACK_DAYS from
// now, or from the current expiry when the pack is still active, so granting
// again before it ends adds another month instead of losing the remainder.
export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  // pro_until is guarded against anon/authenticated writes, so this needs the
  // service client.
  const admin = getSupabaseAdmin()
  if (!admin) return NextResponse.json({ error: "Admin client required" }, { status: 500 })

  const body = await req.json().catch(() => null)
  const userId = typeof body?.userId === "string" ? body.userId : ""
  const action = body?.action
  if (!UUID_RE.test(userId) || (action !== "grant" && action !== "revoke")) {
    return NextResponse.json({ error: "userId and action (grant/revoke) required" }, { status: 400 })
  }

  const { data: current, error: readError } = await admin
    .from("profiles")
    .select("id, email, pro_until")
    .eq("id", userId)
    .maybeSingle()
  if (readError) {
    console.error("[admin/users/pro] read failed:", readError.message)
    return NextResponse.json(
      { error: "Could not read the profile. Has migration 32 (pro_until) been applied?" },
      { status: 500 },
    )
  }
  if (!current) {
    return NextResponse.json({ error: "User has no profile yet. They need to sign in once first." }, { status: 404 })
  }

  let proUntil: string | null = null
  if (action === "grant") {
    const now = Date.now()
    const existing = current.pro_until ? Date.parse(current.pro_until) : NaN
    const start = Number.isNaN(existing) || existing < now ? now : existing
    proUntil = new Date(start + PRO_PACK_DAYS * DAY_MS).toISOString()
  }

  const { error: updateError } = await admin
    .from("profiles")
    .update({ pro_until: proUntil })
    .eq("id", userId)
  if (updateError) {
    console.error("[admin/users/pro] update failed:", updateError.message)
    return NextResponse.json({ error: "Could not update the Pro pack" }, { status: 500 })
  }

  void logAdminAction({
    admin_email: auth.user?.email,
    action: action === "grant" ? "grant_pro_pack" : "revoke_pro_pack",
    entity_type: "user",
    entity_id: userId,
    details: { email: current.email, prev_pro_until: current.pro_until, pro_until: proUntil },
  })

  return NextResponse.json({ success: true, userId, pro_until: proUntil })
}
