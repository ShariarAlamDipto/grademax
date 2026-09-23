import type { Metadata } from "next"
import { redirect } from "next/navigation"
import { listDistricts } from "@/lib/store/catalogue"
import { getSettings } from "@/lib/store/settings"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import CheckoutClient from "@/components/store/CheckoutClient"

export const metadata: Metadata = {
  title: "Checkout",
  robots: { index: false, follow: false },
}

export const dynamic = "force-dynamic"

export interface PrefillDetails {
  name: string
  email: string
  phone: string
  districtId: number | ""
  city: string
  area: string
  houseNo: string
  roadNo: string
  landmark: string
  postcode: string
}

const EMPTY_PREFILL: PrefillDetails = {
  name: "", email: "", phone: "",
  districtId: "", city: "", area: "", houseNo: "", roadNo: "", landmark: "", postcode: "",
}

/**
 * Pre-fill the form from the account, and from the buyer's most recent order.
 *
 * Re-typing a full Bangladeshi address on a phone for every repeat order is the
 * kind of friction that loses the second sale, and the previous order is the
 * best guess available without storing a separate address book.
 */
async function loadPrefill(userId: string, email: string | null, fullName: string | null): Promise<PrefillDetails> {
  const base: PrefillDetails = { ...EMPTY_PREFILL, email: email ?? "", name: fullName ?? "" }

  const db = getSupabaseAdmin()
  if (!db) return base

  const { data: profile } = await db
    .from("profiles")
    .select("full_name, email")
    .eq("id", userId)
    .maybeSingle()

  const withProfile: PrefillDetails = {
    ...base,
    name: base.name || (profile?.full_name ?? ""),
    email: base.email || (profile?.email ?? ""),
  }

  const { data: last } = await db
    .from("store_orders")
    .select("customer_name, customer_phone, customer_email, district_id, city, area, house_no, road_no, landmark, postcode")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle()

  if (!last) return withProfile

  return {
    name: last.customer_name ?? withProfile.name,
    email: last.customer_email ?? withProfile.email,
    phone: last.customer_phone ?? "",
    districtId: last.district_id ?? "",
    city: last.city ?? "",
    area: last.area ?? "",
    houseNo: last.house_no ?? "",
    roadNo: last.road_no ?? "",
    landmark: last.landmark ?? "",
    postcode: last.postcode ?? "",
  }
}

export default async function CheckoutPage() {
  const settings = await getSettings()

  // An account is required, so this is decided on the server before the page is
  // ever rendered — the buyer lands on the sign-in screen, not on a form that
  // fails when they submit it.
  let prefill = EMPTY_PREFILL
  if (settings.requireAccount) {
    const supabase = getSupabaseServer()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) redirect("/login?next=/checkout")
    prefill = await loadPrefill(user.id, user.email ?? null, null)
  }

  const districts = await listDistricts()

  return (
    <CheckoutClient
      districts={districts}
      storeEnabled={settings.storeEnabled}
      wallets={{ bkash: settings.bkashNumber, nagad: settings.nagadNumber }}
      instructions={settings.paymentInstructions}
      slaHours={settings.verificationSlaHours}
      prefill={prefill}
    />
  )
}
