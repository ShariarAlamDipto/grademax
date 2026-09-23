import type { Metadata } from "next"
import { Suspense } from "react"
import StoreOrders from "@/components/admin/store/StoreOrders"

export const metadata: Metadata = { title: "Store orders — Admin" }

export default function AdminStoreOrdersPage() {
  return (
    <Suspense fallback={null}>
      <StoreOrders />
    </Suspense>
  )
}
