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
} satisfies Record<string, RateLimitRule>

/**
 * Best-effort client IP. Vercel sets x-forwarded-for; the left-most entry is
 * the original client. It is spoofable in principle, which is why this is one
 * layer among several rather than the only guard.
 */
export async function getClientIp(): Promise<string> {
  const h = await headers()
  const xff = h.get("x-forwarded-for")
  if (xff) return xff.split(",")[0]!.trim()
  return h.get("x-real-ip") ?? "unknown"
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
