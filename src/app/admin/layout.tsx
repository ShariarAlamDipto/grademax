import type { Metadata } from "next"
import { headers } from "next/headers"
import { redirect } from "next/navigation"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"
import { isTeacherAdminPath, PATHNAME_HEADER, TEACHER_ADMIN_HOME } from "@/lib/adminAccess"
import AdminNav from "@/components/admin/AdminNav"

export const metadata: Metadata = {
  title: "Admin",
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect("/login?next=/admin")
  }

  // Super admin always has access
  let role: "admin" | "teacher" = "admin"
  if (!isSuperAdmin(user.email)) {
    // Read the role with the service client, as src/lib/apiAuth.ts does. The
    // user is already authenticated above, and the cookie client is subject to
    // the profiles RLS policies, whose failure here looks like "not an admin".
    const db = getSupabaseAdmin() || supabase
    const { data: profile, error } = await db
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single()

    if (error) console.error("[admin/layout] profile role lookup failed:", error.message)

    if (profile?.role === "teacher") {
      // Teachers only get the shared sections (workbook verification).
      const pathname = (await headers()).get(PATHNAME_HEADER)
      if (pathname === "/admin") redirect(TEACHER_ADMIN_HOME)
      if (!isTeacherAdminPath(pathname)) redirect("/")
      role = "teacher"
    } else if (profile?.role !== "admin") {
      redirect("/")
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--gm-bg)", color: "var(--gm-text)" }}>
      <AdminNav role={role} />
      <div style={{ flex: 1, minWidth: 0, overflowX: "hidden" }}>
        {children}
      </div>
    </div>
  )
}
