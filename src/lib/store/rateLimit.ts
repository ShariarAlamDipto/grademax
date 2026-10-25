/**
 * Rate limiting for the public store endpoints.
 *
 * Checkout, payment submission and order lookup are all unauthenticated, so
 * without this they are open to brute force: the guest lookup in particular
 * would let someone walk order numbers against phone numbers.
 *
 * The counter lives in Postgres, not in module scope. Vercel runs many
 * short-lived serverless instances and an in-process Map would reset constantly
 * — it would look like a rate limiter while protecting nothing.
 *
 * Failing open is deliberate: if the database counter itself is unreachable the
 * site is already broken, and blocking every checkout would turn a degraded
 * dependency into total downtime.
 */
import { headers } from "next/headers"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export interface RateLimitRule {
  /** Requests permitted per window. */
  limit: number
  /** Window length in seconds. */
  windowSeconds: number
}

export const RATE_LIMITS = {
  checkout:      { limit: 8,  windowSeconds: 600 },  // 8 orders per 10 min per IP
  paymentSubmit: { limit: 10, windowSeconds: 600 },
  orderLookup:   { limit: 12, windowSeconds: 300 },  // brute-force guard
  download:      { limit: 30, windowSeconds: 600 },
  suggestion:    { limit: 5,  windowSeconds: 600 },  // public suggestion box, spam guard
} satisfies Record<string, RateLimitRule>

// IPv4 or IPv6 characters only, so a forged header cannot become a huge or
// odd-looking bucket key.
const IP_RE = /^[0-9a-f.:]{3,45}$/i

/**
 * The client IP, trusted only from headers the client cannot write.
 *
 * Production is Cloudflare → nginx → the container. Cloudflare overwrites
 * CF-Connecting-IP with the real client address. X-Forwarded-For is NOT safe
 * here: Cloudflare and nginx both append to whatever the client sent, so its
 * left-most entry is attacker-chosen. Measured 25 Oct 2026: a different forged
 * X-Forwarded-For on each request walked straight past the order-lookup limit.
 * X-Real-IP is nginx's $remote_addr (a Cloudflare edge address behind
 * Cloudflare, the real client on Vercel or a direct hit), used only as fallback.
 */
export async function getClientIp(): Promise<string> {
  const h = await headers()
  for (const name of ["cf-connecting-ip", "x-real-ip"]) {
    const value = h.get(name)?.trim()
    if (value && IP_RE.test(value)) return value
  }
  return "unknown"
}

/**
 * Returns true when the caller may proceed.
 * `scope` separates the counters, e.g. "checkout:203.0.113.4".
 */
export async function checkRateLimit(
  name: keyof typeof RATE_LIMITS,
  discriminator: string
): Promise<boolean> {
  const rule = RATE_LIMITS[name]
  const db = getSupabaseAdmin()
  if (!db) return true

  try {
    const { data, error } = await db.rpc("store_rate_limit_hit", {
      p_bucket: `${name}:${discriminator}`,
      p_limit: rule.limit,
      p_window_seconds: rule.windowSeconds,
    })
    if (error) return true
    return data !== false
  } catch {
    return true
  }
}

/** Convenience: rate limit the current request by client IP. */
export async function checkRateLimitByIp(name: keyof typeof RATE_LIMITS): Promise<boolean> {
  return checkRateLimit(name, await getClientIp())
}
