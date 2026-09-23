import type { Metadata } from "next"
import StoreOverview from "@/components/admin/store/StoreOverview"

export const metadata: Metadata = { title: "Store — Admin" }

export default function AdminStorePage() {
  return <StoreOverview />
}
