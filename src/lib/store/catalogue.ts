/**
 * Reading the catalogue for public pages.
 *
 * Every query here names its columns explicitly. `SELECT *` would eventually
 * ship `store_variants.r2_key` — the path to the paid PDF — into a page's JSON
 * payload the first time somebody added a field, so the column list is the
 * safeguard and it is deliberate.
 */
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { publicPreviewUrl } from "./r2Store"
import { getSettings } from "./settings"
import type { PublicProduct, PublicVariant, District, VariantKind } from "./types"

interface VariantRow {
  id: string
  kind: VariantKind
  label: string
  price_bdt: number
  compare_at_bdt: number | null
  stock_qty: number | null
  allow_cod: boolean
  page_count: number | null
  is_active: boolean
}

interface ProductRow {
  id: string
  slug: string
  title: string
  subtitle: string | null
  description: string | null
  subject_code: string | null
  spec_summary: string | null
  cover_image_url: string | null
  preview_r2_key: string | null
  preview_pages: number | null
  store_variants: VariantRow[]
}

const PRODUCT_COLUMNS =
  "id, slug, title, subtitle, description, subject_code, spec_summary, " +
  "cover_image_url, preview_r2_key, preview_pages, sort_order, " +
  "store_variants(id, kind, label, price_bdt, compare_at_bdt, stock_qty, allow_cod, page_count, is_active)"

function toPublicVariant(v: VariantRow): PublicVariant {
  return {
    id: v.id,
    kind: v.kind,
    label: v.label,
    price_bdt: v.price_bdt,
    compare_at_bdt: v.compare_at_bdt,
    // A digital file is always in stock; a printed copy is not.
    in_stock: v.kind === "digital" ? true : (v.stock_qty ?? 0) > 0,
    stock_qty: v.kind === "digital" ? null : v.stock_qty,
    allow_cod: v.allow_cod,
    page_count: v.page_count,
  }
}

function toPublicProduct(p: ProductRow, allowDigital: boolean): PublicProduct {
  return {
    id: p.id,
    slug: p.slug,
    title: p.title,
    subtitle: p.subtitle,
    description: p.description,
    subject_code: p.subject_code,
    spec_summary: p.spec_summary,
    cover_image_url: p.cover_image_url,
    preview_url: publicPreviewUrl(p.preview_r2_key),
    preview_pages: p.preview_pages,
    variants: (p.store_variants ?? [])
      .filter(v => v.is_active)
      // While downloads are switched off, the PDF variant must not appear in
      // any payload at all -- not greyed out, not "coming soon". A variant the
      // buyer can see is a variant they will try to order.
      .filter(v => allowDigital || v.kind === "print")
      .sort((x, y) => (x.kind === "print" ? 0 : 1) - (y.kind === "print" ? 0 : 1))
      .map(toPublicVariant),
  }
}

export async function listActiveProducts(): Promise<PublicProduct[]> {
  const db = getSupabaseAdmin()
  if (!db) return []
  const { data, error } = await db
    .from("store_products")
    .select(PRODUCT_COLUMNS)
    .eq("is_active", true)
    .order("sort_order", { ascending: true })
  if (error || !data) return []
  const { digitalSalesEnabled } = await getSettings()
  return (data as unknown as ProductRow[])
    .map(p => toPublicProduct(p, digitalSalesEnabled))
    .filter(p => p.variants.length > 0)
}

export async function getProductBySlug(slug: string): Promise<PublicProduct | null> {
  const db = getSupabaseAdmin()
  if (!db) return null
  const { data, error } = await db
    .from("store_products")
    .select(PRODUCT_COLUMNS)
    .eq("slug", slug)
    .eq("is_active", true)
    .maybeSingle()
  if (error || !data) return null
  const { digitalSalesEnabled } = await getSettings()
  const product = toPublicProduct(data as unknown as ProductRow, digitalSalesEnabled)
  return product.variants.length > 0 ? product : null
}

export async function listDistricts(): Promise<District[]> {
  const db = getSupabaseAdmin()
  if (!db) return []
  const { data, error } = await db
    .from("store_districts")
    .select("id, name, division, is_metro")
    .eq("is_active", true)
    .order("sort_order", { ascending: true })
    .order("name", { ascending: true })
  if (error || !data) return []
  return data as District[]
}
