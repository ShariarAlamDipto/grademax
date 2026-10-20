// Validates a caller-supplied `next`/redirect path so it can only ever point
// back to a same-site location. Prevents open-redirect abuse where a crafted
// `?next=` value bounces a freshly authenticated user off to an attacker's
// origin (a classic phishing/credential-relay vector).
//
// The bugs this closes:
//   "//evil.com"       -> new URL(x, origin) resolves to https://evil.com
//   "/\evil.com"       -> browsers treat backslash as a path separator
//   "https://evil.com" -> absolute URL
// Only a single-slash, non-backslash, relative path is allowed through.

import { SITE_URL } from "./metadata"

const DEFAULT_PATH = "/dashboard"

// True if the string contains any ASCII control character (0x00-0x1F or 0x7F).
// Some URL parsers strip tab/newline, which can smuggle a host boundary across
// the leading slash, so any control char disqualifies the path.
function hasControlChar(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i)
    if (code <= 0x1f || code === 0x7f) return true
  }
  return false
}

export function safeNextPath(raw: string | null | undefined, fallback: string = DEFAULT_PATH): string {
  if (!raw) return fallback

  // Must be a root-relative path...
  if (!raw.startsWith("/")) return fallback
  // ...but NOT protocol-relative ("//host") or backslash-tricked ("/\host").
  if (raw.startsWith("//") || raw.startsWith("/\\")) return fallback
  if (hasControlChar(raw)) return fallback

  // Final defense: resolve against a throwaway origin and confirm it stays there.
  try {
    const probe = "https://x.invalid"
    const resolved = new URL(raw, probe)
    if (resolved.origin !== probe) return fallback
    // Preserve path + query + hash only.
    return resolved.pathname + resolved.search + resolved.hash
  } catch {
    return fallback
  }
}

// Origin to build post-login redirects on. Behind a proxy, a self-hosted
// `next start` (Docker, HOSTNAME=0.0.0.0) builds request.url from its bind
// address, so redirecting to `new URL(request.url).origin` sent every user who
// signed in to https://0.0.0.0:3000. Only GradeMax's own hosts are trusted from
// the Host / X-Forwarded-Host headers, so a forged header cannot turn this into
// an open redirect; anything else falls back to the canonical site.
const PUBLIC_HOSTS = new Set(["www.grademax.me", "grademax.me"])
const LOCAL_HOST_RE = /^(localhost|127\.0\.0\.1)(:\d+)?$/

export function publicOrigin(request: Request): string {
  const headers = request.headers
  const forwarded = headers.get("x-forwarded-host")?.split(",")[0]?.trim().toLowerCase()
  const host = forwarded || headers.get("host")?.trim().toLowerCase() || new URL(request.url).host

  if (PUBLIC_HOSTS.has(host)) return `https://${host}`
  if (LOCAL_HOST_RE.test(host)) return `${new URL(request.url).protocol}//${host}`
  return SITE_URL
}
