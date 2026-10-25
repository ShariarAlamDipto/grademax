import { after } from "next/server"
import { cookies, headers } from "next/headers"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { SESSION_COOKIE, VISITOR_COOKIE, isAnalyticsEnabled, isVisitorId, parseCountry } from "@/lib/siteVisits"

/**
 * Behaviour events the server records itself, for the analytics funnels.
 *
 * The browser cannot send these (parseBeacon refuses them), so an order or a
 * sign-in in the funnels is one that really happened. They are tied to the
 * visit through the anonymous gm_vid / gm_sid cookies the request carries; a
 * request without a tracked visitor (a bot, cookies blocked) records nothing.
 */
export type ServerEventName =
  | "sign_in" | "sign_up" | "sign_in_failed" | "order_placed"
  | "worksheet_generated" | "worksheet_failed" | "test_generated" | "test_failed" | "limit_reached"

/** Small numeric/boolean facts about an event (counts, timings). Never free text from users. */
export type EventProps = Record<string, number | boolean | null>

const MAX_LABEL_LENGTH = 200
const MAX_PROPS = 12
// The events migration 37 already accepts.
const LEGACY_EVENTS = new Set<ServerEventName>(["sign_in", "sign_up", "order_placed", "worksheet_generated", "test_generated"])

function cleanProps(props: EventProps | undefined): EventProps | null {
  if (!props) return null
  const entries = Object.entries(props)
    .filter(([key, value]) => /^[a-z_]{1,32}$/.test(key) && (value === null || typeof value === "boolean" || Number.isFinite(value)))
    .slice(0, MAX_PROPS)
  return entries.length ? Object.fromEntries(entries) : null
}

/**
 * Queues the event to be written after the response is sent. Never throws and
 * never delays the response: analytics must not cost the user anything.
 */
export async function trackServerEvent(
  name: ServerEventName, path: string, label?: string | null, props?: EventProps
): Promise<void> {
  try {
    if (!isAnalyticsEnabled()) return
    const jar = await cookies()
    const visitorId = jar.get(VISITOR_COOKIE)?.value
    if (!isVisitorId(visitorId)) return
    const requestHeaders = await headers()
    if (requestHeaders.get("sec-gpc") === "1") return
    const sessionId = jar.get(SESSION_COOKIE)?.value
    const base = {
      visitor_id: visitorId,
      session_id: isVisitorId(sessionId) ? sessionId : null,
      name,
      label: label ? label.slice(0, MAX_LABEL_LENGTH) : null,
      path,
    }
    const extra = { country: parseCountry(requestHeaders.get("cf-ipcountry")), props: cleanProps(props) }
    after(async () => {
      const db = getSupabaseAdmin()
      if (!db) return
      const { error } = await db.from("site_events").insert({ ...base, ...extra })
      // PGRST204 (no country/props column) or 23514 (event name not allowed
      // yet): migration 38 is not applied. Keep the events 37 understands.
      if (error?.code === "PGRST204" || error?.code === "23514") {
        if (!LEGACY_EVENTS.has(name)) return
        const { error: retryError } = await db.from("site_events").insert(base)
        if (retryError) console.error(`[site-events] ${name} insert failed (${retryError.code ?? "no code"}): ${retryError.message}`)
        return
      }
      if (error) console.error(`[site-events] ${name} insert failed (${error.code ?? "no code"}): ${error.message}`)
    })
  } catch (error: unknown) {
    console.error(`[site-events] could not queue ${name}:`, error instanceof Error ? error.message : error)
  }
}
