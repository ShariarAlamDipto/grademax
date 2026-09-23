import type { Metadata } from "next"
import CartClient from "@/components/store/CartClient"

export const metadata: Metadata = {
  title: "Your cart",
  robots: { index: false, follow: false },
}

export default function CartPage() {
  return <CartClient />
}
