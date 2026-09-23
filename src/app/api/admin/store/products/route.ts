import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { logAdminAction } from "@/lib/auditLog"
import { adminProductUpdateSchema, adminVariantUpdateSchema } from "@/lib/store/schemas"
import { isStoreBucketConfigured, storeObjectExists } from "@/lib/store/r2Store"

/**
 * Admin catalogue: prices, stock, and the switch that puts a product on sale.
 *
 * Activating a product is guarded. A digital variant with no uploaded file
 * would take money for something that cannot be delivered, so the file is
 * checked in the private bucket before the product can go live.
 */
export const dynamic = "force-dynamic"

export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Unavailable" }, { status: 503 })

  const { data, error } = await db
    .from("store_products")
    .select(
      "id, slug, title, subtitle, description, subject_code, spec_summary, preview_r2_key, preview_pages, is_active, sort_order, " +
      "store_variants(id, kind, label, price_bdt, stock_qty, allow_cod, is_active, page_count)"
    )
    .order("sort_order", { ascending: true })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  // File counts per variant, so the UI can show what is ready to sell.
  const { data: files } = await db.from("store_variant_files").select("id, variant_id, label, file_name, file_bytes")
  const filesByVariant = new Map<string, unknown[]>()
  for (const f of (files ?? []) as { variant_id: string }[]) {
    const list = filesByVariant.get(f.variant_id) ?? []
    list.push(f)
    filesByVariant.set(f.variant_id, list)
  }

  type AdminProductRow = Record<string, unknown> & { store_variants?: { id: string }[] }

  const products = ((data ?? []) as unknown as AdminProductRow[]).map(p => ({
    ...p,
    store_variants: (p.store_variants ?? []).map(v => ({
      ...v,
      files: filesByVariant.get(v.id) ?? [],
    })),
  }))

  return NextResponse.json({
    products,
    storeBucketConfigured: isStoreBucketConfigured(),
  })
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

  const payload = body as { variant?: unknown; product?: unknown }

  // ── Variant edit: price, stock, availability ──
  if (payload.variant) {
    const parsed = adminVariantUpdateSchema.safeParse(payload.variant)
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.issues[0]?.message ?? "Invalid input." }, { status: 400 })
    }
    const { variantId, priceBdt, stockQty, isActive, label } = parsed.data

    const { data: existing } = await db
      .from("store_variants")
      .select("kind, price_bdt, stock_qty")
      .eq("id", variantId)
      .maybeSingle()
    if (!existing) return NextResponse.json({ error: "Variant not found." }, { status: 404 })

    const patch: Record<string, unknown> = { updated_at: new Date().toISOString() }
    if (priceBdt !== undefined) patch.price_bdt = priceBdt
    if (isActive !== undefined) patch.is_active = isActive
    if (label !== undefined) patch.label = label
    // A digital variant must keep stock NULL — the table constraint enforces it,
    // so silently dropping the field gives a clearer error than a 500.
    if (stockQty !== undefined && existing.kind === "print") patch.stock_qty = stockQty

    const { error } = await db.from("store_variants").update(patch).eq("id", variantId)
    if (error) return NextResponse.json({ error: error.message }, { status: 400 })

    await logAdminAction({
      admin_email: auth.user.email,
      action: "store_update_variant",
      entity_type: "store_variant",
      entity_id: variantId,
      details: {
        price_from: existing.price_bdt, price_to: priceBdt ?? existing.price_bdt,
        stock_from: existing.stock_qty, stock_to: stockQty ?? existing.stock_qty,
      },
    })
    return NextResponse.json({ ok: true })
  }

  // ── Product edit, including the on-sale switch ──
  if (payload.product) {
    const parsed = adminProductUpdateSchema.safeParse(payload.product)
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.issues[0]?.message ?? "Invalid input." }, { status: 400 })
    }
    const { productId, isActive, title, subtitle, description, sortOrder } = parsed.data

    if (isActive === true) {
      const blocked = await reasonProductCannotGoLive(productId)
      if (blocked) return NextResponse.json({ error: blocked }, { status: 409 })
    }

    const patch: Record<string, unknown> = { updated_at: new Date().toISOString() }
    if (isActive !== undefined) patch.is_active = isActive
    if (title !== undefined) patch.title = title
    if (subtitle !== undefined) patch.subtitle = subtitle
    if (description !== undefined) patch.description = description
    if (sortOrder !== undefined) patch.sort_order = sortOrder

    const { error } = await db.from("store_products").update(patch).eq("id", productId)
    if (error) return NextResponse.json({ error: error.message }, { status: 400 })

    await logAdminAction({
      admin_email: auth.user.email,
      action: "store_update_product",
      entity_type: "store_product",
      entity_id: productId,
      details: { is_active: isActive ?? null },
    })
    return NextResponse.json({ ok: true })
  }

  return NextResponse.json({ error: "Nothing to update." }, { status: 400 })
}

/**
 * Returns a human-readable reason a product must not go on sale yet, or null.
 * Checked at the moment of activation rather than trusted from a flag, because
 * a file can be removed from the bucket after a product was first switched on.
 */
async function reasonProductCannotGoLive(productId: string): Promise<string | null> {
  const db = getSupabaseAdmin()
  if (!db) return "The store is temporarily unavailable."

  const { data: variants } = await db
    .from("store_variants")
    .select("id, kind, price_bdt, is_active")
    .eq("product_id", productId)
    .eq("is_active", true)

  if (!variants?.length) return "This product has no active variants to sell."

  const rows = variants as { id: string; kind: string; price_bdt: number }[]

  const unpriced = rows.find(v => v.price_bdt <= 0)
  if (unpriced) {
    return `Set a price for the ${unpriced.kind} version before putting this on sale.`
  }

  const digital = rows.filter(v => v.kind === "digital")
  if (digital.length > 0) {
    if (!isStoreBucketConfigured()) {
      return "R2_STORE_BUCKET is not configured, so digital downloads cannot be delivered. " +
             "Set it, or deactivate the digital version before going live."
    }
    for (const v of digital) {
      const { data: files } = await db
        .from("store_variant_files")
        .select("r2_key, label")
        .eq("variant_id", v.id)
      if (!files?.length) {
        return "Upload the PDF files for the digital version before putting this on sale."
      }
      for (const f of files as { r2_key: string; label: string }[]) {
        if (!(await storeObjectExists(f.r2_key))) {
          return `The file for "${f.label}" is missing from the private bucket. Upload it before going live.`
        }
      }
    }
  }

  return null
}
