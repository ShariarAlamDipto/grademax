import { redirect } from "next/navigation"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { isSuperAdmin } from "@/lib/supabaseAdmin"
import AdminNav from "@/components/admin/AdminNav"

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect("/login?next=/admin")
  }

  // Super admin always has access
  if (!isSuperAdmin(user.email)) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single()

    if (profile?.role !== "admin") {
      redirect("/")
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--gm-bg)", color: "var(--gm-text)" }}>
      <AdminNav />
      <div style={{ flex: 1, minWidth: 0, overflowX: "hidden" }}>
        {children}
      </div>
    </div>
  )
}
