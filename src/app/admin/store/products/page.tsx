import type { Metadata } from "next"
import StoreProducts from "@/components/admin/store/StoreProducts"

export const metadata: Metadata = { title: "Store products — Admin" }

export default function AdminStoreProductsPage() {
  return <StoreProducts />
}
