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
