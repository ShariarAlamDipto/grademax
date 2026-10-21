import { NextResponse } from "next/server"

// Liveness probe for the Docker healthcheck, the deploy script and the server
// watchdog. It answers from the Node process alone, with no Supabase or R2 call,
// so a slow upstream never marks a working container as dead and gets it
// restarted. It must stay cheap: it runs every 30 seconds.
export const dynamic = "force-dynamic"

export function GET() {
  return NextResponse.json(
    { ok: true, uptime: Math.round(process.uptime()) },
    { headers: { "Cache-Control": "no-store" } }
  )
}
