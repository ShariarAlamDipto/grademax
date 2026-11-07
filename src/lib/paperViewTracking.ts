import { isBotUserAgent, isVisitorId } from "@/lib/siteVisits"

/**
 * Which /viewer renders count as a paper being opened (usage_events.paper_view).
 *
 * The viewer is rendered on the server, so the count used to include every
 * client whose user agent did not say "bot". On live data (30 Oct–6 Nov 2026)
 * that was 92,803 opens a week against 4,793 /viewer page views from real
 * browsers: scrapers with browser user agents were roughly 19 of every 20.
 *
 * A render now counts only when the request carries the anonymous visitor
 * cookie (gm_vid), which /api/visit sets only for a browser that ran the
 * tracker on an earlier page. A reader whose very first page is the viewer is
 * missed on that one render; everything after it counts.
 */
export interface PaperViewRequest {
  hasPdf: boolean
  userAgent: string
  headers: Headers
  visitorId: string | undefined
}

/** A prefetch (Next.js router or the browser's speculative loading) is not a paper being opened. */
export function isPrefetch(h: Headers): boolean {
  return h.get("next-router-prefetch") === "1"
    || /prefetch|prerender/i.test(h.get("sec-purpose") ?? h.get("purpose") ?? "")
}

export function shouldCountPaperView(req: PaperViewRequest): boolean {
  return req.hasPdf
    && !isBotUserAgent(req.userAgent)
    && !isPrefetch(req.headers)
    // Global Privacy Control: the reader asked not to be tracked.
    && req.headers.get("sec-gpc") !== "1"
    && isVisitorId(req.visitorId)
}
