import type { Metadata } from "next"

// Metadata-only layout: the page is a client component and cannot export metadata itself.
export const metadata: Metadata = {
  title: "My Profile",
}

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return children
}
