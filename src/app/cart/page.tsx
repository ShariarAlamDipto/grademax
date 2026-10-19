import type { Metadata } from "next"
import CartClient from "@/components/store/CartClient"
import { getSettings } from "@/lib/store/settings"

export const metadata: Metadata = {
  title: "Your cart",
  robots: { index: false, follow: false },
}

// The delivery rates are shown here, and they change from the admin portal.
export const dynamic = "force-dynamic"

export default async function CartPage() {
  const settings = await getSettings()
  return (
    <CartClient
      deliveryMetroBdt={settings.deliveryBdtMetro}
      deliveryOutsideBdt={settings.deliveryBdtOutside}
      freeDeliveryOverBdt={settings.freeDeliveryOverBdt}
    />
  )
}
