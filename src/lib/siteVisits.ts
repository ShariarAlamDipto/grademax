/**
 * First-party visitor analytics: the pure helpers behind /api/visit.
 *
 * Vercel Analytics stopped counting when the site moved to the self-hosted
 * Docker server, so page views are now recorded in our own `site_visits` table
 * (migration 36). Nothing personal is stored: no IP address, no user id, no
 * query string. A visitor is an anonymous random UUID kept in the `gm_vid`
 * cookie, which is what lets the dashboard count unique visitors per day.
 */

export type Device = "mobile" | "tablet" | "desktop"

export const VISITOR_COOKIE = "gm_vid"
export const VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

const MAX_PATH_LENGTH = 300
const MAX_HOST_LENGTH = 120
const OWN_HOSTS = new Set(["grademax.me", "www.grademax.me"])
// Staff pages and API calls are not visits.
const UNTRACKED_PREFIXES = ["/admin", "/api", "/_next"]

// Same family as the /viewer paper_view filter, plus empty agents and the
// common HTTP libraries. A real browser always sends a user agent.
const BOT_UA = /bot|crawl|spider|slurp|preview|curl|wget|python|axios|node-fetch|go-http|java\/|headless|lighthouse|facebookexternalhit|scrapy|httpclient/i

// Printable ASCII with no spaces, quotes or angle brackets. Browsers send
// non-ASCII paths percent-encoded, so real pages always pass.
const PATH_RE = /^\/[A-Za-z0-9\-._~%!$&'()*+,;=:@/]*$/
const OWN_ORIGINS = new Set(["https://www.grademax.me", "https://grademax.me"])
const DEV_ORIGIN_RE = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/

const UUID_RE =/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function isBotUserAgent(userAgent: string): boolean {
  return !userAgent.trim() || BOT_UA.test(userAgent)
}

export function classifyDevice(userAgent: string): Device {
  if (/ipad|tablet|kindle|silk/i.test(userAgent)) return "tablet"
  // Android tablets omit "Mobile"; Android phones include it.
  if (/android/i.test(userAgent) && !/mobile/i.test(userAgent)) return "tablet"
  if (/mobi|iphone|ipod|android|windows phone/i.test(userAgent)) return "mobile"
  return "desktop"
}

/** The pathname to record, or null when the value is not a trackable page. */
export function sanitizeVisitPath(value: unknown): string | null {
  if (typeof value !== "string") return null
  const path = value.split(/[?#]/)[0] ?? ""
  if (!PATH_RE.test(path) || path.startsWith("//")) return null
  if (path.length > MAX_PATH_LENGTH) return null
  const isUntracked = UNTRACKED_PREFIXES.some(prefix => path === prefix || path.startsWith(`${prefix}/`))
  return isUntracked ? null : path
}

/** Host of an external referrer ("www." dropped); null for our own site or junk. */
export function externalReferrerHost(referrer: unknown): string | null {
  if (typeof referrer !== "string" || !referrer) return null
  try {
    const host = new URL(referrer).hostname.toLowerCase()
    if (!host || OWN_HOSTS.has(host) || host.length > MAX_HOST_LENGTH) return null
    return host.replace(/^www\./, "")
  } catch {
    return null
  }
}

/** Cloudflare's CF-IPCountry header; "XX" (unknown) and "T1" (Tor) are dropped. */
export function parseCountry(header: string | null): string | null {
  if (!header || !/^[a-z]{2}$/i.test(header)) return null
  const code = header.toUpperCase()
  return code === "XX" || code === "T1" ? null : code
}

/** Whether the request carries a Supabase session cookie (chunked or not). */
export function hasSupabaseSession(cookieNames: readonly string[]): boolean {
  return cookieNames.some(name => /^sb-.+-auth-token(\.\d+)?$/.test(name))
}

export function isVisitorId(value: string | undefined): value is string {
  return typeof value === "string" && UUID_RE.test(value)
}

/**
 * Browsers always send Origin on a POST, including sendBeacon. Requiring ours
 * stops other sites from posting fake visits through their visitors' browsers.
 */
export function isAllowedOrigin(origin: string | null, isProduction: boolean): boolean {
  if (!origin) return false
  return OWN_ORIGINS.has(origin) || (!isProduction && DEV_ORIGIN_RE.test(origin))
}

export interface HitCounter {
  /** Records a hit; false once `key` is over the limit for the current window. */
  hit(key: string): boolean
  size(): number
}

/**
 * Fixed-window counter held in memory. Enough for the visit beacon because
 * production is one long-running container; a restart only resets the caps.
 * `maxKeys` bounds memory: when full, expired windows are dropped first and,
 * failing that, the whole map is cleared rather than growing.
 */
export function createHitCounter(opts: {
  limit: number
  windowMs: number
  maxKeys: number
  now?: () => number
}): HitCounter {
  const now = opts.now ?? Date.now
  const windows = new Map<string, { start: number; hits: number }>()

  const prune = (t: number) => {
    for (const [key, w] of windows) if (t - w.start >= opts.windowMs) windows.delete(key)
    if (windows.size >= opts.maxKeys) windows.clear()
  }

  return {
    hit(key) {
      const t = now()
      const current = windows.get(key)
      if (current && t - current.start < opts.windowMs) {
        windows.set(key, { start: current.start, hits: current.hits + 1 })
        return current.hits + 1 <= opts.limit
      }
      if (!current && windows.size >= opts.maxKeys) prune(t)
      windows.set(key, { start: t, hits: 1 })
      return true
    },
    size: () => windows.size,
  }
}
