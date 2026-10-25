import { NextRequest, NextResponse } from "next/server"
import { randomUUID } from "node:crypto"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getClientIp } from "@/lib/store/rateLimit"
import {
  VISITOR_COOKIE,
  VISITOR_COOKIE_MAX_AGE,
  classifyDevice,
  createHitCounter,
  externalReferrerHost,
  hasSupabaseSession,
  isAllowedOrigin,
  isBotUserAgent,
  isVisitorId,
  parseCountry,
  sanitizeVisitPath,
} from "@/lib/siteVisits"

/**
 * POST /api/visit — record one page view for Admin → Analytics → Visitors.
 *
 * Sent by <VisitTracker /> with navigator.sendBeacon, so nobody reads the
 * response: it always answers 204 and a failure only costs one counted view.
 * Pages are statically cached, which is why this is a beacon and not a
 * server-side insert during render.
 */
export const dynamic = "force-dynamic"

const MAX_BODY_BYTES = 2048
const IS_PRODUCTION = process.env.NODE_ENV === "production"

// Anyone can post here, so each IP is capped. A real reader opens far fewer
// than 120 pages in 10 minutes; a script flooding the table does not get far.
// In memory rather than the store's Postgres limiter, which would double the
// database writes of every page view.
const perIp = createHitCounter({ limit: 120, windowMs: 10 * 60 * 1000, maxKeys: 50_000 })

export async function POST(req: NextRequest) {
  const done = new NextResponse(null, { status: 204 })

  if (!isAllowedOrigin(req.headers.get("origin"), IS_PRODUCTION)) return done
  const userAgent = req.headers.get("user-agent") ?? ""
  if (isBotUserAgent(userAgent)) return done
  if (Number(req.headers.get("content-length") ?? 0) > MAX_BODY_BYTES) return done
  if (!perIp.hit(await getClientIp())) return done

  let body: { path?: unknown; referrer?: unknown }
  try {
    const raw = await readBounded(req, MAX_BODY_BYTES)
    if (raw === null) return done
    body = JSON.parse(raw)
  } catch {
    return done
  }

  const path = sanitizeVisitPath(body?.path)
  if (!path) return done

  const existing = req.cookies.get(VISITOR_COOKIE)?.value
  const isNewVisitor = !isVisitorId(existing)
  const visitorId = isNewVisitor ? randomUUID() : existing

  const db = getSupabaseAdmin()
  if (db) {
    const { error } = await db.from("site_visits").insert({
      visitor_id: visitorId,
      is_new_visitor: isNewVisitor,
      signed_in: hasSupabaseSession(req.cookies.getAll().map(c => c.name)),
      path,
      referrer_host: externalReferrerHost(body.referrer),
      country: parseCountry(req.headers.get("cf-ipcountry")),
      device: classifyDevice(userAgent),
    })
    if (error) console.error(`[visit] insert failed (${error.code ?? "no code"}): ${error.message}`)
  }

  if (isNewVisitor) {
    done.cookies.set(VISITOR_COOKIE, visitorId, {
      httpOnly: true,
      secure: IS_PRODUCTION,
      sameSite: "lax",
      path: "/",
      maxAge: VISITOR_COOKIE_MAX_AGE,
    })
  }
  return done
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
