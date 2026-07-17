import type { Metadata } from "next"

// Metadata-only layout: the page is a client component and cannot export metadata itself.
export const metadata: Metadata = {
  title: "Teacher Dashboard",
}

export default function TeacherDashboardLayout({ children }: { children: React.ReactNode }) {
  return children
}
