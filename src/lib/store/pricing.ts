/**
 * Server-side pricing. This is the security boundary of the whole store.
 *
 * The browser sends only variant IDs and quantities. It never sends a price,
 * and any price it did send would be ignored: every figure below is read from
 * `store_variants` at the moment of checkout. A tampered cart therefore cannot
 * buy an 800-Taka workbook for 1 Taka.
 *
 * The same function prices the cart summary the buyer sees and the order that
 * is actually written, so the two can never disagree.
 */
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getSettings } from "./settings"
import type {
  CartLineInput, PricedCart, PricedLine, PaymentMethod, VariantKind,
} from "./types"

export type PricingError =
  | { code: "empty_cart"; message: string }
  | { code: "unknown_variant"; message: string; variantId: string }
  | { code: "inactive_variant"; message: string; variantId: string }
  | { code: "out_of_stock"; message: string; variantId: string; available: number }
  | { code: "quantity_too_high"; message: string; variantId: string; max: number }
  | { code: "unavailable"; message: string }
  | { code: "digital_disabled"; message: string; variantId: string }

export type PricingResult =
  | { ok: true; cart: PricedCart }
  | { ok: false; error: PricingError }

interface VariantRow {
  id: string
  product_id: string
  kind: VariantKind
  label: string
  price_bdt: number
  stock_qty: number | null
  allow_cod: boolean
  is_active: boolean
  store_products: { title: string; is_active: boolean } | null
}

/**
 * Delivery is charged once per order, not per item, and only when something
 * physical is actually being shipped. A digital-only order ships nothing and is
 * charged nothing, however many files it contains.
 */
export async function calculateDelivery(
  hasPrint: boolean,
  isMetro: boolean,
  subtotalBdt: number
): Promise<number> {
  if (!hasPrint) return 0
  const s = await getSettings()
  if (s.freeDeliveryOverBdt > 0 && subtotalBdt >= s.freeDeliveryOverBdt) return 0
  return isMetro ? s.deliveryBdtMetro : s.deliveryBdtOutside
}

/**
 * Price a cart from the database.
 *
 * `isMetro` decides the delivery band. It is unknown until the buyer picks a
 * district, so the cart page passes undefined and shows delivery as "calculated
 * at checkout" rather than guessing low and surprising them later.
 */
export async function priceCart(
  lines: CartLineInput[],
  opts: { isMetro?: boolean } = {}
): Promise<PricingResult> {
  if (!lines.length) {
    return { ok: false, error: { code: "empty_cart", message: "Your cart is empty." } }
  }

  const db = getSupabaseAdmin()
  if (!db) {
    return { ok: false, error: { code: "unavailable", message: "The store is temporarily unavailable." } }
  }

  const settings = await getSettings()

  // Collapse duplicate lines for the same variant before anything else, so
  // sending the same variant ten times cannot slip past the per-line cap.
  const wanted = new Map<string, number>()
  for (const line of lines) {
    const qty = Math.floor(Number(line.quantity))
    if (!Number.isFinite(qty) || qty < 1) continue
    wanted.set(line.variantId, (wanted.get(line.variantId) ?? 0) + qty)
  }
  if (wanted.size === 0) {
    return { ok: false, error: { code: "empty_cart", message: "Your cart is empty." } }
  }

  const { data, error } = await db
    .from("store_variants")
    .select("id, product_id, kind, label, price_bdt, stock_qty, allow_cod, is_active, store_products(title, is_active)")
    .in("id", [...wanted.keys()])

  if (error || !data) {
    return { ok: false, error: { code: "unavailable", message: "Could not price your cart." } }
  }

  const rows = data as unknown as VariantRow[]
  const byId = new Map(rows.map(r => [r.id, r]))

  const priced: PricedLine[] = []
  for (const [variantId, quantity] of wanted) {
    const v = byId.get(variantId)
    if (!v) {
      return { ok: false, error: { code: "unknown_variant", message: "An item in your cart no longer exists.", variantId } }
    }
    // Downloads are not on sale. A cart holding one is stale -- most likely a
    // localStorage cart from before the change -- so it is refused with an
    // explanation rather than silently repriced.
    if (v.kind === "digital" && !settings.digitalSalesEnabled) {
      return {
        ok: false,
        error: {
          code: "digital_disabled", variantId,
          message: "PDF downloads are not on sale at the moment. Please remove that item and order the printed copy instead.",
        },
      }
    }
    if (!v.is_active || !v.store_products?.is_active) {
      return { ok: false, error: { code: "inactive_variant", message: `${v.store_products?.title ?? "An item"} is not on sale right now.`, variantId } }
    }

    // A digital file has no unit count worth buying twice, and a per-line cap
    // keeps an unauthenticated endpoint from being used to reserve all stock.
    const max = v.kind === "digital" ? 1 : settings.maxUnitsPerOrder
    if (quantity > max) {
      return {
        ok: false,
        error: {
          code: "quantity_too_high", variantId, max,
          message: v.kind === "digital"
            ? "One copy of a digital download is enough — it never expires."
            : `You can order at most ${max} copies of one title.`,
        },
      }
    }

    if (v.kind === "print" && (v.stock_qty ?? 0) < quantity) {
      return {
        ok: false,
        error: {
          code: "out_of_stock", variantId, available: v.stock_qty ?? 0,
          message: (v.stock_qty ?? 0) === 0
            ? `${v.store_products.title} is out of stock.`
            : `Only ${v.stock_qty} copies of ${v.store_products.title} are left.`,
        },
      }
    }

    priced.push({
      variantId: v.id,
      productId: v.product_id,
      productTitle: v.store_products.title,
      variantLabel: v.label,
      kind: v.kind,
      unitPriceBdt: v.price_bdt,
      quantity,
      lineTotalBdt: v.price_bdt * quantity,
    })
  }

  const subtotalBdt = priced.reduce((sum, l) => sum + l.lineTotalBdt, 0)
  const hasPrint = priced.some(l => l.kind === "print")
  const hasDigital = priced.some(l => l.kind === "digital")

  const deliveryBdt = opts.isMetro === undefined
    ? 0
    : await calculateDelivery(hasPrint, opts.isMetro, subtotalBdt)

  // Cash on delivery cannot collect money for a download, so a cart holding any
  // digital item loses that option entirely. Mixing the two would otherwise
  // hand over the PDF before any money changed hands.
  const allowedPaymentMethods: PaymentMethod[] = hasDigital
    ? ["bkash", "nagad"]
    : ["bkash", "nagad", "cod"]

  return {
    ok: true,
    cart: {
      lines: priced,
      subtotalBdt,
      deliveryBdt,
      discountBdt: 0,
      totalBdt: subtotalBdt + deliveryBdt,
      hasPrint,
      hasDigital,
      allowedPaymentMethods,
    },
  }
}
