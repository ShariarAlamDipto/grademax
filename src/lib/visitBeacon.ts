/**
 * Sends one analytics beacon to /api/visit (see siteBehavior.ts for the
 * types). sendBeacon survives the page closing; fetch with keepalive is the
 * fallback. Never throws and nobody waits for it.
 */
export function sendVisitBeacon(payload: Record<string, unknown>): void {
  const body = JSON.stringify(payload)
  try {
    if (navigator.sendBeacon?.("/api/visit", new Blob([body], { type: "application/json" }))) return
  } catch {
    // Fall through to fetch.
  }
  fetch("/api/visit", { method: "POST", body, keepalive: true, headers: { "Content-Type": "application/json" } })
    .catch(() => {})
}
