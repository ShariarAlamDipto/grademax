import { NextResponse } from "next/server"
import { listActiveProducts, listDistricts } from "@/lib/store/catalogue"
import { getSettings } from "@/lib/store/settings"

/**
 * GET /api/store/products — the public catalogue.
 *
 * Reads with the service key and returns an explicit, safe projection. The
 * browser never touches `store_variants` directly, so `r2_key` cannot leak.
 */
export const dynamic = "force-dynamic"

export async function GET() {
  const settings = await getSettings()
  if (!settings.storeEnabled) {
    return NextResponse.json({ enabled: false, products: [], districts: [] })
  }

  const [products, districts] = await Promise.all([listActiveProducts(), listDistricts()])

  return NextResponse.json({
    enabled: true,
    products,
    districts,
    delivery: {
      metroBdt: settings.deliveryBdtMetro,
      outsideBdt: settings.deliveryBdtOutside,
      freeOverBdt: settings.freeDeliveryOverBdt,
    },
  })
}
