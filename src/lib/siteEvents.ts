import { after } from "next/server"
import { cookies } from "next/headers"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { SESSION_COOKIE, VISITOR_COOKIE, isVisitorId } from "@/lib/siteVisits"

/**
 * Behaviour events the server records itself, for the analytics funnels.
 *
 * The browser cannot send these (parseBeacon refuses them), so an order or a
 * sign-in in the funnels is one that really happened. They are tied to the
 * visit through the anonymous gm_vid / gm_sid cookies the request carries; a
 * request without a tracked visitor (a bot, cookies blocked) records nothing.
 */
export type ServerEventName = "sign_in" | "sign_up" | "order_placed" | "worksheet_generated" | "test_generated"

const MAX_LABEL_LENGTH = 200

/**
 * Queues the event to be written after the response is sent. Never throws and
 * never delays the response: analytics must not cost the user anything.
 */
export async function trackServerEvent(name: ServerEventName, path: string, label?: string | null): Promise<void> {
  try {
    const jar = await cookies()
    const visitorId = jar.get(VISITOR_COOKIE)?.value
    if (!isVisitorId(visitorId)) return
    const sessionId = jar.get(SESSION_COOKIE)?.value
    const row = {
      visitor_id: visitorId,
      session_id: isVisitorId(sessionId) ? sessionId : null,
      name,
      label: label ? label.slice(0, MAX_LABEL_LENGTH) : null,
      path,
    }
    after(async () => {
      const db = getSupabaseAdmin()
      if (!db) return
      const { error } = await db.from("site_events").insert(row)
      if (error) console.error(`[site-events] ${name} insert failed (${error.code ?? "no code"}): ${error.message}`)
    })
  } catch (error: unknown) {
    console.error(`[site-events] could not queue ${name}:`, error instanceof Error ? error.message : error)
  }
}
