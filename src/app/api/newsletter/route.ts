import { NextRequest, NextResponse } from "next/server"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export async function POST(req: NextRequest) {
  try {
    const { email } = await req.json()

    if (!email || typeof email !== "string" || !email.includes("@")) {
      return NextResponse.json({ error: "Invalid email address." }, { status: 400 })
    }

    const normalised = email.trim().toLowerCase()

    const db = getSupabaseAdmin()
    if (!db) {
      return NextResponse.json({ error: "Service unavailable." }, { status: 503 })
    }

    const { error } = await db
      .from("newsletter_subscribers")
      .upsert({ email: normalised, subscribed_at: new Date().toISOString() }, { onConflict: "email", ignoreDuplicates: true })

    if (error) {
      console.error("newsletter upsert error:", error.message)
      return NextResponse.json({ error: "Could not subscribe. Please try again." }, { status: 500 })
    }

    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: "Could not subscribe. Please try again." }, { status: 500 })
  }
}
