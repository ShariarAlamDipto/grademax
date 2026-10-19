import type { Metadata } from "next"

// Metadata-only layout: the page is a client component and cannot export metadata itself.
export const metadata: Metadata = {
  title: "Lectures",
}

export default function LecturesLayout({ children }: { children: React.ReactNode }) {
  return children
}
