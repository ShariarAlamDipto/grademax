import type { Metadata } from "next"
import { Suspense } from "react"
import OrderTracker from "@/components/store/OrderTracker"

export const metadata: Metadata = {
  title: "Track your order",
  description: "Check the status of a GradeMax book order and get your download links.",
  robots: { index: false, follow: false },
}

export default function TrackOrderPage() {
  return (
    <Suspense fallback={null}>
      <OrderTracker />
    </Suspense>
  )
}
