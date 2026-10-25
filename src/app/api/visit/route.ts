import { NextRequest, NextResponse, after } from "next/server"
import { randomUUID } from "node:crypto"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getClientIp } from "@/lib/store/rateLimit"
import {
  SESSION_COOKIE,
  SESSION_COOKIE_MAX_AGE,
  VISITOR_COOKIE,
  VISITOR_COOKIE_MAX_AGE,
  classifyDevice,
  createHitCounter,
  externalReferrerHost,
  hasSupabaseSession,
  isAllowedOrigin,
  isAnalyticsEnabled,
  isBotUserAgent,
  isVisitorId,
  parseCountry,
} from "@/lib/siteVisits"
import { type Beacon, classifyChannel, parseBeacon, parseBrowser, parseOs } from "@/lib/siteBehavior"
import { runAnalyticsAlerts } from "@/lib/analyticsAlerts"

/**
 * POST /api/visit — behaviour beacons for Admin → Analytics → Visitors.
 *
 * Sent by <VisitTracker /> with navigator.sendBeacon, so nobody reads the
 * response: it always answers 204 and a failure only costs one data point.
 * Pages are statically cached, which is why this is a beacon and not a
 * server-side insert during render. See siteBehavior.ts for the beacon types.
 */
export const dynamic = "force-dynamic"

const MAX_BODY_BYTES = 2048
const IS_PRODUCTION = process.env.NODE_ENV === "production"

// Anyone can post here, so each IP is capped. A reader sends a page view, an
// engagement update and the odd click per page; 300 beacons in 10 minutes is
// far beyond real reading, and a script flooding the tables does not get far.
// In memory rather than the store's Postgres limiter, which would double the
// database writes of every page view.
const perIp = createHitCounter({ limit: 300, windowMs: 10 * 60 * 1000, maxKeys: 50_000 })

// Raw rows older than 13 months are deleted (privacy policy). Roughly one page
// view in 2,000 triggers the purge, after the response; it is an indexed delete.
const PURGE_CHANCE = 1 / 2000
const RETENTION_MONTHS = 13
const ALERT_CHANCE = 1 / 20

type Db = NonNullable<ReturnType<typeof getSupabaseAdmin>>

export async function POST(req: NextRequest) {
  const done = new NextResponse(null, { status: 204 })

  if (!isAnalyticsEnabled()) return done
  // Global Privacy Control: the visitor asked not to be tracked.
  if (req.headers.get("sec-gpc") === "1") return done
  if (!isAllowedOrigin(req.headers.get("origin"), IS_PRODUCTION)) return done
  const userAgent = req.headers.get("user-agent") ?? ""
  if (isBotUserAgent(userAgent)) return done
  if (Number(req.headers.get("content-length") ?? 0) > MAX_BODY_BYTES) return done
  if (!perIp.hit(await getClientIp())) return done

  let beacon: Beacon | null
  try {
    const raw = await readBounded(req, MAX_BODY_BYTES)
    beacon = raw === null ? null : parseBeacon(JSON.parse(raw))
  } catch {
    return done
  }
  if (!beacon) return done

  const db = getSupabaseAdmin()
  if (!db) return done

  const existingVisitor = req.cookies.get(VISITOR_COOKIE)?.value
  const existingSession = req.cookies.get(SESSION_COOKIE)?.value

  // Engagement and clicks belong to a visit that already sent a page view.
  if (beacon.type !== "pageview") {
    if (!isVisitorId(existingVisitor)) return done
    if (beacon.type === "engage") {
      const { error } = await db.rpc("site_visit_engage", {
        p_pv: beacon.pv, p_visitor: existingVisitor, p_seconds: beacon.seconds, p_scroll: beacon.scroll,
      })
      if (error) logError("engage", error)
    } else if (beacon.type === "vital") {
      const { error } = await db.rpc("site_visit_vital", {
        p_pv: beacon.pv, p_visitor: existingVisitor, p_name: beacon.name, p_value: beacon.value,
      })
      // PGRST202: migration 40 not applied yet; vitals are simply not kept.
      if (error && error.code !== "PGRST202") logError("vital", error)
    } else {
      const event = {
        visitor_id: existingVisitor,
        session_id: isVisitorId(existingSession) ? existingSession : null,
        name: beacon.name, label: beacon.label, path: beacon.path,
      }
      const { error } = await db.from("site_events").insert({ ...event, country: parseCountry(req.headers.get("cf-ipcountry")) })
      // PGRST204: migration 38 (site_events.country) not applied yet.
      const retry = error?.code === "PGRST204" ? (await db.from("site_events").insert(event)).error : error
      if (retry) logError("event", retry)
    }
    return done
  }

  // Alert rules are evaluated at most every 15 minutes by the database itself;
  // a page view now and then is just what wakes the check up.
  if (Math.random() < ALERT_CHANCE) after(() => runAnalyticsAlerts(db))

  if (Math.random() < PURGE_CHANCE) {
    after(async () => {
      const { error } = await db.rpc("site_analytics_purge", { p_months: RETENTION_MONTHS })
      if (error && error.code !== "PGRST202") logError("purge", error)
    })
  }

  const isNewVisitor = !isVisitorId(existingVisitor)
  const visitorId = isNewVisitor ? randomUUID() : existingVisitor
  const isSessionStart = !isVisitorId(existingSession)
  const sessionId = isSessionStart ? randomUUID() : existingSession

  await insertPageView(db, req, beacon, { visitorId, sessionId, isNewVisitor, isSessionStart, userAgent })

  const cookieBase = { httpOnly: true, secure: IS_PRODUCTION, sameSite: "lax" as const, path: "/" }
  if (isNewVisitor) done.cookies.set(VISITOR_COOKIE, visitorId, { ...cookieBase, maxAge: VISITOR_COOKIE_MAX_AGE })
  // Re-set on every page view: the session lasts until 30 idle minutes pass.
  done.cookies.set(SESSION_COOKIE, sessionId, { ...cookieBase, maxAge: SESSION_COOKIE_MAX_AGE })
  return done
}

async function insertPageView(
  db: Db,
  req: NextRequest,
  beacon: Extract<Beacon, { type: "pageview" }>,
  ids: { visitorId: string; sessionId: string; isNewVisitor: boolean; isSessionStart: boolean; userAgent: string }
): Promise<void> {
  const referrerHost = externalReferrerHost(beacon.referrer)
  // Where the visit came from only means something on its first page.
  const source = ids.isSessionStart
    ? {
        channel: classifyChannel(referrerHost, beacon.utm),
        utm_source: beacon.utm.source,
        utm_medium: beacon.utm.medium,
        utm_campaign: beacon.utm.campaign,
      }
    : {}

  // The columns from migration 36; everything else needs migration 37.
  const base = {
    visitor_id: ids.visitorId,
    is_new_visitor: ids.isNewVisitor,
    signed_in: hasSupabaseSession(req.cookies.getAll().map(c => c.name)),
    path: beacon.path,
    referrer_host: referrerHost,
    country: parseCountry(req.headers.get("cf-ipcountry")),
    device: classifyDevice(ids.userAgent),
  }
  const { error } = await db.from("site_visits").insert({
    ...base,
    pv_id: beacon.pv,
    session_id: ids.sessionId,
    is_session_start: ids.isSessionStart,
    browser: parseBrowser(ids.userAgent),
    os: parseOs(ids.userAgent),
    ...source,
  })
  if (!error || error.code === "23505") return // 23505: a retried beacon, already stored.
  if (error.code === "PGRST204") {
    // Migration 37 not applied yet: keep counting visits with what exists.
    const { error: retryError } = await db.from("site_visits").insert(base)
    if (retryError) logError("pageview", retryError)
    return
  }
  logError("pageview", error)
}

function logError(kind: string, error: { code?: string; message: string }): void {
  console.error(`[visit] ${kind} failed (${error.code ?? "no code"}): ${error.message}`)
}

/** The body as text, or null once it passes `limit` bytes (chunked bodies have no Content-Length). */
async function readBounded(req: NextRequest, limit: number): Promise<string | null> {
  if (!req.body) return ""
  const reader = req.body.getReader()
  const chunks: Uint8Array[] = []
  let size = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    size += value.byteLength
    if (size > limit) {
      await reader.cancel()
      return null
    }
    chunks.push(value)
  }
  return Buffer.concat(chunks).toString("utf8")
}
