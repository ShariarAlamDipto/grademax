/**
 * Behaviour analytics: the pure helpers for /api/visit beyond the page view
 * itself. They classify where a visit came from, which browser and OS it used,
 * and validate the three beacon types the tracker sends:
 *
 *   pageview  one per page, carries a client-made page-view id (pv)
 *   engage    active seconds and scroll depth for a pv, sent when the reader
 *             leaves the page or hides the tab (the server keeps the maximum)
 *   event     a PDF download or an outbound link click
 *
 * Events the server records itself (orders, sign-ins, generated worksheets)
 * are never accepted from a browser; see SERVER_EVENTS in siteEvents.ts.
 */
import { isVisitorId, sanitizeVisitPath } from "@/lib/siteVisits"

export type Channel = "direct" | "search" | "social" | "ai" | "email" | "paid" | "referral"
export type BrowserEventName = "download" | "outbound" | "js_error" | "gate_shown"
export type VitalName = "LCP" | "INP" | "CLS" | "FCP" | "TTFB"

export interface Utm {
  source: string | null
  medium: string | null
  campaign: string | null
}

export type Beacon =
  | { type: "pageview"; pv: string | null; path: string; referrer: string | null; utm: Utm }
  | { type: "engage"; pv: string; seconds: number; scroll: number }
  | { type: "event"; name: BrowserEventName; label: string; path: string }
  | { type: "vital"; pv: string; name: VitalName; value: number }

const MAX_UTM_LENGTH = 100
const MAX_LABEL_LENGTH = 200
const MAX_ENGAGED_SECONDS = 86_400
const UTM_RE = /^[a-z0-9 _.+-]+$/
// gate_shown: the free sign-in prompt after the daily download limit (DownloadGate).
const BROWSER_EVENTS = new Set<BrowserEventName>(["download", "outbound", "js_error", "gate_shown"])
// Upper bounds well past anything real; larger values are measurement junk.
const VITAL_MAX: Record<VitalName, number> = { LCP: 120_000, INP: 60_000, CLS: 50, FCP: 120_000, TTFB: 120_000 }
// Errors we cannot act on: cross-origin scripts (ads), a harmless browser
// warning, and scripts the browser itself injects (Firefox and Chrome on iOS
// run reader-mode/translate helpers that throw on our pages; seen live 26 Oct).
const NOISE_ERRORS = /^(Uncaught )?(Script error\.?|ResizeObserver loop)|__firefox__|__gCrWeb|webkit\.messageHandlers|instantSearchSDKJSBridge/i
const EXTENSION_URL = /^(chrome|moz|safari|safari-web|ms-browser)-extension:/i

// Checked in this order: AI before search, because gemini.google.com is Google.
const AI_HOSTS = /(^|\.)(chatgpt\.com|chat\.openai\.com|openai\.com|perplexity\.ai|gemini\.google\.com|bard\.google\.com|copilot\.microsoft\.com|claude\.ai|poe\.com|you\.com|deepseek\.com|meta\.ai|grok\.com)$/
const SEARCH_HOSTS = /(^|\.)(google\.[a-z.]+|bing\.com|duckduckgo\.com|yahoo\.[a-z.]+|yandex\.[a-z.]+|baidu\.com|ecosia\.org|search\.brave\.com|naver\.com|startpage\.com)$/
const SOCIAL_HOSTS = /(^|\.)(facebook\.com|fb\.com|messenger\.com|instagram\.com|t\.co|x\.com|twitter\.com|youtube\.com|youtu\.be|reddit\.com|linkedin\.com|lnkd\.in|pinterest\.[a-z.]+|tiktok\.com|discord\.com|discord\.gg|wa\.me|whatsapp\.com|t\.me|telegram\.org|quora\.com|threads\.net)$/
const PAID_MEDIUMS = new Set(["cpc", "ppc", "paid", "paidsocial", "paid_social", "display", "ads", "cpm"])
const SOCIAL_SOURCES = /facebook|instagram|fb|youtube|tiktok|twitter|x\.com|linkedin|whatsapp|telegram|discord|reddit|messenger/
const SEARCH_SOURCES = /google|bing|yahoo|duckduckgo/

export function sanitizeUtm(value: unknown): string | null {
  if (typeof value !== "string") return null
  const tag = value.trim().toLowerCase()
  if (!tag || tag.length > MAX_UTM_LENGTH || !UTM_RE.test(tag)) return null
  return tag
}

/** The marketing channel of a visit's first page. */
export function classifyChannel(referrerHost: string | null, utm: Pick<Utm, "source" | "medium">): Channel {
  const medium = utm.medium ?? ""
  const source = utm.source ?? ""
  if (PAID_MEDIUMS.has(medium)) return "paid"
  if (medium === "email" || /newsletter|mailchimp|email/.test(source)) return "email"
  if (referrerHost) {
    if (AI_HOSTS.test(referrerHost)) return "ai"
    if (SEARCH_HOSTS.test(referrerHost)) return "search"
    if (SOCIAL_HOSTS.test(referrerHost)) return "social"
    return "referral"
  }
  if (source) {
    if (SOCIAL_SOURCES.test(source)) return "social"
    if (SEARCH_SOURCES.test(source)) return "search"
    if (/chatgpt|openai|perplexity|gemini|copilot|claude/.test(source)) return "ai"
    return "referral"
  }
  return "direct"
}

export function parseBrowser(userAgent: string): string {
  if (/FBAN|FBAV|FB_IAB/.test(userAgent)) return "Facebook app"
  if (/Instagram/.test(userAgent)) return "Instagram app"
  if (/Edg(e|A|iOS)?\//.test(userAgent)) return "Edge"
  if (/OPR\/|Opera/.test(userAgent)) return "Opera"
  if (/SamsungBrowser/.test(userAgent)) return "Samsung Internet"
  if (/Firefox\/|FxiOS/.test(userAgent)) return "Firefox"
  if (/Chrome\/|CriOS/.test(userAgent)) return "Chrome"
  if (/Safari\//.test(userAgent)) return "Safari"
  return "Other"
}

export function parseOs(userAgent: string): string {
  if (/iPhone|iPad|iPod/.test(userAgent)) return "iOS"
  if (/Android/.test(userAgent)) return "Android"
  if (/CrOS/.test(userAgent)) return "ChromeOS"
  if (/Windows/.test(userAgent)) return "Windows"
  if (/Mac OS X|Macintosh/.test(userAgent)) return "macOS"
  if (/Linux/.test(userAgent)) return "Linux"
  return "Other"
}

function clampInt(value: unknown, min: number, max: number): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null
  return Math.min(max, Math.max(min, Math.floor(value)))
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

/** Validates a beacon body; null for anything malformed or not allowed. */
export function parseBeacon(value: unknown): Beacon | null {
  const body = asRecord(value)
  if (!body) return null
  const type = body.type ?? "pageview"

  if (type === "pageview") {
    const path = sanitizeVisitPath(body.path)
    if (!path) return null
    const pv = typeof body.pv === "string" && isVisitorId(body.pv) ? body.pv : null
    const utm = asRecord(body.utm)
    return {
      type, pv, path,
      referrer: typeof body.referrer === "string" && body.referrer ? body.referrer.slice(0, 500) : null,
      utm: { source: sanitizeUtm(utm?.source), medium: sanitizeUtm(utm?.medium), campaign: sanitizeUtm(utm?.campaign) },
    }
  }

  if (type === "engage") {
    if (typeof body.pv !== "string" || !isVisitorId(body.pv)) return null
    const seconds = clampInt(body.seconds, 0, MAX_ENGAGED_SECONDS)
    const scroll = clampInt(body.scroll, 0, 100)
    if (seconds === null || scroll === null) return null
    return { type, pv: body.pv, seconds, scroll }
  }

  if (type === "event") {
    const name = body.name as BrowserEventName
    const path = sanitizeVisitPath(body.path)
    if (!BROWSER_EVENTS.has(name) || !path || typeof body.label !== "string" || !body.label) return null
    return { type, name, label: body.label.slice(0, MAX_LABEL_LENGTH), path }
  }

  if (type === "vital") {
    const name = body.name as VitalName
    if (typeof body.pv !== "string" || !isVisitorId(body.pv) || !Object.hasOwn(VITAL_MAX, name)) return null
    const value = body.value
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > VITAL_MAX[name]) return null
    // CLS is a unitless score (0.1 is "good"); the others are milliseconds.
    return { type, pv: body.pv, name, value: name === "CLS" ? Math.round(value * 1000) / 1000 : Math.round(value) }
  }

  return null
}

/** Strips query strings (they can hold tokens) from URLs inside text. */
function stripQueries(text: string): string {
  return text.replace(/(https?:\/\/[^\s?#"']+)[?#][^\s"']*/g, "$1")
}

/**
 * A short, safe label for a browser error: "message @ /path/file.js:line".
 * Null for errors we cannot act on (cross-origin, extensions, known noise).
 */
export function sanitizeErrorLabel(message: string, filename: string, line: number): string | null {
  const text = stripQueries(String(message ?? "").trim())
  if (!text || NOISE_ERRORS.test(text) || EXTENSION_URL.test(filename)) return null
  let where = ""
  if (filename) {
    try {
      const url = new URL(filename)
      const isOurs = url.hostname === "grademax.me" || url.hostname.endsWith(".grademax.me")
      where = ` @ ${isOurs ? url.pathname : url.hostname + url.pathname}${line ? `:${line}` : ""}`
    } catch {
      where = ""
    }
  }
  return `${text}${where}`.slice(0, MAX_LABEL_LENGTH)
}

/** What a link click means for analytics, or null when it is an ordinary internal link. */
export function classifyLinkClick(href: string, currentHost: string): { name: BrowserEventName; label: string } | null {
  let url: URL
  try {
    url = new URL(href)
  } catch {
    return null
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null
  const isPdf = /\.pdf$/i.test(url.pathname) || /(^|\.)r2\.dev$|r2\.cloudflarestorage\.com$/.test(url.hostname)
  if (isPdf) return { name: "download", label: decodeSafe(url.pathname).slice(0, MAX_LABEL_LENGTH) }
  if (url.hostname === currentHost) return null
  return { name: "outbound", label: url.hostname.replace(/^www\./, "") }
}

function decodeSafe(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}
