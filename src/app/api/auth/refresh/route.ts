import { NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"

export async function POST() {
  // Touch the server client so auth cookies get updated
  const supabase = getSupabaseServer()
  await supabase.auth.getUser()
  return NextResponse.json({ ok: true })
}
