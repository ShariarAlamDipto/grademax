/**
 * While a reader stays active on one page (building a worksheet, reading a
 * paper), an engagement update is sent every five minutes of active time.
 * /api/visit refreshes the 30-minute session cookie on it, so a long stay on
 * one page is one visit, and the tool events it produces keep their visit.
 * Before this, 16% of worksheet_generated events had no visit at all.
 */
export const HEARTBEAT_SECONDS = 300

export function isHeartbeatDue(seconds: number, sentSeconds: number): boolean {
  return seconds - sentSeconds >= HEARTBEAT_SECONDS
}

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
