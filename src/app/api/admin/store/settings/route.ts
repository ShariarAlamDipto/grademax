import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { logAdminAction } from "@/lib/auditLog"
import { adminSettingsSchema } from "@/lib/store/schemas"
import { invalidateSettingsCache } from "@/lib/store/settings"

/**
 * Store settings: delivery charges, the bKash/Nagad numbers buyers pay into,
 * and the master on/off switch.
 *
 * Turning the store on is guarded: without a wallet number on file, every buyer
 * reaches the payment step and has nowhere to send the money.
 */
export const dynamic = "force-dynamic"

export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Unavailable" }, { status: 503 })

  const { data, error } = await db
    .from("store_settings")
    .select("key, value, description, updated_at")
    .order("key", { ascending: true })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ settings: data ?? [] })
}

export async function PATCH(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Unavailable" }, { status: 503 })

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 })
  }

  const parsed = adminSettingsSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input." }, { status: 400 })
  }
  const updates = parsed.data.updates

  // Only keys that already exist may be written, so this cannot be used to
  // insert arbitrary rows.
  const { data: known } = await db.from("store_settings").select("key, value")
  const current = new Map((known ?? []).map((r: { key: string; value: string }) => [r.key, r.value]))

  const unknownKey = Object.keys(updates).find(k => !current.has(k))
  if (unknownKey) {
    return NextResponse.json({ error: `Unknown setting: ${unknownKey}` }, { status: 400 })
  }

  // Numeric settings must parse as non-negative integers — a typo in a delivery
  // charge would otherwise be stored and break every later checkout.
  const numericKeys = ["delivery_bdt_metro", "delivery_bdt_outside", "free_delivery_over_bdt",
                       "verification_sla_hours", "max_units_per_order"]
  for (const key of numericKeys) {
    if (key in updates && !/^\d+$/.test(updates[key]!.trim())) {
      return NextResponse.json({ error: `${key} must be a whole number.` }, { status: 400 })
    }
  }

  const merged = new Map(current)
  for (const [k, v] of Object.entries(updates)) merged.set(k, v)

  if ((merged.get("store_enabled") ?? "").toLowerCase() === "true") {
    const bkash = (merged.get("bkash_number") ?? "").trim()
    const nagad = (merged.get("nagad_number") ?? "").trim()
    if (!bkash && !nagad) {
      return NextResponse.json(
        { error: "Add a bKash or Nagad number before opening the store — buyers need somewhere to send payment." },
        { status: 409 }
      )
    }
  }

  for (const [key, value] of Object.entries(updates)) {
    const { error } = await db
      .from("store_settings")
      .update({ value, updated_at: new Date().toISOString() })
      .eq("key", key)
    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  }

  invalidateSettingsCache()

  await logAdminAction({
    admin_email: auth.user.email,
    action: "store_update_settings",
    entity_type: "store_settings",
    // Values are not logged: two of these keys are wallet numbers.
    details: { keys: Object.keys(updates) },
  })

  return NextResponse.json({ ok: true })
}
