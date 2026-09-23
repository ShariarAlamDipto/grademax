/**
 * Store settings, read from the `store_settings` table.
 *
 * Delivery charges and the bKash/Nagad numbers live in the database rather than
 * in source so the owner can change them from the admin portal without a
 * deploy — and so a wallet number is never committed to a public repository.
 *
 * Values are cached briefly per server instance. Checkout re-reads them anyway
 * through `getSettings()`, and a few seconds of staleness on a delivery charge
 * is acceptable; minutes of it would not be.
 */
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export interface StoreSettings {
  deliveryBdtMetro: number
  deliveryBdtOutside: number
  freeDeliveryOverBdt: number
  bkashNumber: string
  nagadNumber: string
  paymentInstructions: string
  verificationSlaHours: number
  storeEnabled: boolean
  maxUnitsPerOrder: number
  /** Sell PDF downloads as well as printed copies. Off for now. */
  digitalSalesEnabled: boolean
  /** Buyers must sign in before ordering. */
  requireAccount: boolean
}

const DEFAULTS: StoreSettings = {
  deliveryBdtMetro: 70,
  deliveryBdtOutside: 130,
  freeDeliveryOverBdt: 0,
  bkashNumber: "",
  nagadNumber: "",
  paymentInstructions: "",
  verificationSlaHours: 12,
  storeEnabled: false,
  maxUnitsPerOrder: 10,
  digitalSalesEnabled: false,
  requireAccount: true,
}

const CACHE_MS = 15_000
let cache: { at: number; value: StoreSettings } | null = null

function toInt(raw: string | undefined, fallback: number): number {
  const n = Number.parseInt(raw ?? "", 10)
  return Number.isFinite(n) && n >= 0 ? n : fallback
}

export async function getSettings(force = false): Promise<StoreSettings> {
  if (!force && cache && Date.now() - cache.at < CACHE_MS) return cache.value

  const db = getSupabaseAdmin()
  if (!db) return DEFAULTS

  const { data, error } = await db.from("store_settings").select("key, value")
  if (error || !data) return DEFAULTS

  const raw: Record<string, string> = Object.fromEntries(
    data.map((r: { key: string; value: string }) => [r.key, r.value])
  )

  const value: StoreSettings = {
    deliveryBdtMetro:    toInt(raw.delivery_bdt_metro, DEFAULTS.deliveryBdtMetro),
    deliveryBdtOutside:  toInt(raw.delivery_bdt_outside, DEFAULTS.deliveryBdtOutside),
    freeDeliveryOverBdt: toInt(raw.free_delivery_over_bdt, DEFAULTS.freeDeliveryOverBdt),
    bkashNumber:         raw.bkash_number ?? "",
    nagadNumber:         raw.nagad_number ?? "",
    paymentInstructions: raw.payment_instructions ?? DEFAULTS.paymentInstructions,
    verificationSlaHours: toInt(raw.verification_sla_hours, DEFAULTS.verificationSlaHours),
    storeEnabled:        (raw.store_enabled ?? "false").toLowerCase() === "true",
    maxUnitsPerOrder:    Math.max(1, toInt(raw.max_units_per_order, DEFAULTS.maxUnitsPerOrder)),
    // Both default to the safe answer when the row is missing: do not sell
    // downloads, and do not let anyone order without an account.
    digitalSalesEnabled: (raw.digital_sales_enabled ?? "false").toLowerCase() === "true",
    requireAccount:      (raw.require_account ?? "true").toLowerCase() === "true",
  }

  cache = { at: Date.now(), value }
  return value
}

/** Drop the cache after an admin edit so the change is visible immediately. */
export function invalidateSettingsCache(): void {
  cache = null
}

export async function setSetting(key: string, value: string): Promise<boolean> {
  const db = getSupabaseAdmin()
  if (!db) return false
  const { error } = await db
    .from("store_settings")
    .update({ value, updated_at: new Date().toISOString() })
    .eq("key", key)
  invalidateSettingsCache()
  return !error
}
