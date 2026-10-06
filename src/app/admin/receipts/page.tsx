import type { Metadata } from "next"
import { Suspense } from "react"
import ReceiptBuilder from "@/components/admin/receipts/ReceiptBuilder"

export const metadata: Metadata = { title: "Receipts — Admin" }

export default function AdminReceiptsPage() {
  return (
    <Suspense fallback={null}>
      <ReceiptBuilder />
    </Suspense>
  )
}
