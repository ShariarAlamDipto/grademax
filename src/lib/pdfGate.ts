/**
 * Throttled, short-lived access to the PDFs in the papers bucket.
 *
 * WHY
 * ---
 * The papers bucket is served from a public `pub-*.r2.dev` host, and until now
 * every page printed those URLs straight into its HTML. Anyone could point a
 * "download all links" extension or a ten-line script at the catalogue and walk
 * away with the whole archive, year by year and chapter by chapter.
 *
 * Now the browser only ever gets:
 *   - a key in a viewer link, which the viewer turns into a signed link per
 *     request, after a per-IP rate limit;
 *   - a /api/pdf/<key> link for downloads, which does the same and redirects;
 *   - signed links in the worksheet and test-builder API responses, which are
 *     signed-in, rate limited and capped in size.
 *
 * Signed links point at the S3 endpoint, not the public host, and expire. Until
 * public access on the bucket is switched off a determined person who already
 * knows the public host and key layout can still guess URLs; the rate limits
 * and the absence of URLs in the HTML are what make bulk copying hard today.
 * Set PDF_PRESIGN=off to fall back to public URLs (still rate limited) if the
 * bucket's CORS policy turns out not to cover the S3 endpoint.
 *
 * Server-only: imports the R2 client and credentials.
 */
import { GetObjectCommand } from "@aws-sdk/client-s3"
import { getSignedUrl } from "@aws-sdk/s3-request-presigner"
import { headers } from "next/headers"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { checkRateLimitRule, getClientIp, type RateLimitRule } from "@/lib/store/rateLimit"
import { publicUrlForPdfKey, r2KeyFromUrl } from "@/lib/viewer-link"

/** How long a signed link handed to the viewer or the tools stays valid. */
export const PDF_LINK_TTL_SECONDS = 2 * 60 * 60

/**
 * Per-IP allowances. A student revising opens a handful of papers an hour; a
 * scraper wants hundreds a minute. Schools share one IP, so the daily ceilings
 * are generous rather than tight.
 */
export const PDF_LIMITS = {
  /** Papers opened in the viewer. */
  viewBurst:     { limit: 40,  windowSeconds: 600 },
  viewDaily:     { limit: 300, windowSeconds: 86_400 },
  /** Direct downloads through /api/pdf. */
  fileBurst:     { limit: 30,  windowSeconds: 600 },
  fileDaily:     { limit: 200, windowSeconds: 86_400 },
} satisfies Record<string, RateLimitRule>

/**
 * Download tools and HTTP libraries that announce themselves. Trivially
 * spoofed, but it stops the lazy end of bulk copying at no cost to a person in
 * a browser. Search engine crawlers are deliberately not on this list.
 */
const SCRAPER_UA =
  /\b(curl|wget|python-requests|python-urllib|aiohttp|httpx|go-http-client|java\/|okhttp|libwww|lwp::|httrack|webcopier|webzip|teleport|offline explorer|sitesucker|scrapy|node-fetch|axios|undici|postmanruntime|powershell|winhttp|aria2|idm|internet download manager|jdownloader|getright|flashget|wkhtmltopdf)\b/i

export async function isScraperRequest(): Promise<boolean> {
  const ua = (await headers()).get("user-agent") ?? ""
  return ua.trim() === "" || SCRAPER_UA.test(ua)
}

/** Both windows must allow it. Each call spends one unit from each. */
export async function allowPdfAccess(kind: "view" | "file", units = 1): Promise<boolean> {
  const ip = await getClientIp()
  const [burst, daily] = kind === "view"
    ? [PDF_LIMITS.viewBurst, PDF_LIMITS.viewDaily]
    : [PDF_LIMITS.fileBurst, PDF_LIMITS.fileDaily]
  for (let i = 0; i < units; i++) {
    const okBurst = await checkRateLimitRule(`pdf:${kind}:burst:${ip}`, burst)
    const okDaily = await checkRateLimitRule(`pdf:${kind}:daily:${ip}`, daily)
    if (!okBurst || !okDaily) return false
  }
  return true
}

/** Per-signed-in-user allowance for the tools that hand out many page links. */
export async function allowUserAction(name: string, userId: string, rules: RateLimitRule[]): Promise<boolean> {
  for (const [i, rule] of rules.entries()) {
    if (!(await checkRateLimitRule(`tool:${name}:${i}:${userId}`, rule))) return false
  }
  return true
}

function presignEnabled(): boolean {
  return (process.env.PDF_PRESIGN ?? "on").toLowerCase() !== "off"
}

/**
 * A signed link to one key, or the public URL if signing is off or fails. The
 * fallback keeps the site working through an R2 credential problem; the rate
 * limit in front of it still applies.
 */
export async function signedPdfUrl(
  key: string,
  opts: { ttlSeconds?: number; downloadName?: string } = {}
): Promise<string> {
  if (!presignEnabled()) return publicUrlForPdfKey(key)
  try {
    const name = opts.downloadName?.replace(/["\\\r\n]/g, "").slice(0, 180)
    const command = new GetObjectCommand({
      Bucket: R2_BUCKET,
      Key: key,
      ResponseContentType: "application/pdf",
      ...(name ? { ResponseContentDisposition: `attachment; filename="${name}"` } : {}),
    })
    return await getSignedUrl(getR2Client(), command, {
      expiresIn: opts.ttlSeconds ?? PDF_LINK_TTL_SECONDS,
    })
  } catch (error) {
    console.error("[pdfGate] could not sign", key, error instanceof Error ? error.message : error)
    return publicUrlForPdfKey(key)
  }
}

/** Sign a URL if it is a bucket PDF; anything else is returned unchanged. */
export async function signIfBucketPdf<T extends string | null | undefined>(url: T): Promise<T | string> {
  const key = r2KeyFromUrl(url)
  return key ? signedPdfUrl(key) : url
}
