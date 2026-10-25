"use client"
import { usePathname } from "next/navigation"
import { useEffect, useRef } from "react"
import { classifyLinkClick } from "@/lib/siteBehavior"

/**
 * Anonymous behaviour beacons for the admin Visitors dashboard (/api/visit).
 *
 *  - pageview: once per navigation. Only the pathname is sent, plus
 *    document.referrer and utm_* tags on the first page of the tab.
 *  - engage:   active reading time and deepest scroll for that page view,
 *    sent when the reader moves on or hides the tab. Time only counts while
 *    the tab is visible and the reader did something in the last minute.
 *  - event:    clicks on PDF links (downloads) and links to other sites.
 */
const IDLE_MS = 60_000
const TICK_MS = 1_000
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "mousemove", "touchstart", "wheel"] as const

interface PageState {
  pv: string | null
  path: string | null
  seconds: number
  scroll: number
  lastActive: number
  sentSeconds: number
  sentScroll: number
  isFirstView: boolean
}

function send(payload: Record<string, unknown>): void {
  const body = JSON.stringify(payload)
  try {
    if (navigator.sendBeacon?.("/api/visit", new Blob([body], { type: "application/json" }))) return
  } catch {
    // Fall through to fetch.
  }
  fetch("/api/visit", { method: "POST", body, keepalive: true, headers: { "Content-Type": "application/json" } })
    .catch(() => {})
}

function newPageViewId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID()
  // Older browsers: RFC 4122 v4 from getRandomValues.
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = Array.from(b, x => x.toString(16).padStart(2, "0")).join("")
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

function scrollPercent(): number {
  const height = document.documentElement.scrollHeight
  if (height <= window.innerHeight) return 100
  return Math.min(100, Math.round(((window.scrollY + window.innerHeight) / height) * 100))
}

function readUtm(): Record<string, string | null> {
  const params = new URLSearchParams(window.location.search)
  return { source: params.get("utm_source"), medium: params.get("utm_medium"), campaign: params.get("utm_campaign") }
}

function flushEngagement(s: PageState): void {
  if (!s.pv || (s.seconds === s.sentSeconds && s.scroll === s.sentScroll)) return
  send({ type: "engage", pv: s.pv, seconds: s.seconds, scroll: s.scroll })
  s.sentSeconds = s.seconds
  s.sentScroll = s.scroll
}

export default function VisitTracker() {
  const pathname = usePathname()
  const state = useRef<PageState>({
    pv: null, path: null, seconds: 0, scroll: 0, lastActive: 0, sentSeconds: 0, sentScroll: 0, isFirstView: true,
  })

  // Listeners live for the whole visit; the ref holds the current page view.
  useEffect(() => {
    if (navigator.webdriver) return
    const s = state.current
    const markActive = () => { s.lastActive = Date.now() }
    const onScroll = () => { markActive(); s.scroll = Math.max(s.scroll, scrollPercent()) }
    const onVisibility = () => (document.visibilityState === "hidden" ? flushEngagement(s) : markActive())
    const onPageHide = () => flushEngagement(s)
    const onClick = (event: MouseEvent) => {
      const link = (event.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null
      if (!link || !s.pv || !s.path) return
      // hostname, not host: a port (dev) would make every internal link "outbound".
      const hit = classifyLinkClick(link.href, window.location.hostname)
      if (hit) send({ type: "event", name: hit.name, label: hit.label, path: s.path })
    }
    const timer = window.setInterval(() => {
      if (s.pv && document.visibilityState === "visible" && Date.now() - s.lastActive < IDLE_MS) s.seconds += 1
    }, TICK_MS)

    ACTIVITY_EVENTS.forEach(name => window.addEventListener(name, markActive, { passive: true }))
    window.addEventListener("scroll", onScroll, { passive: true })
    document.addEventListener("visibilitychange", onVisibility)
    window.addEventListener("pagehide", onPageHide)
    document.addEventListener("click", onClick, true)
    document.addEventListener("auxclick", onClick, true)
    return () => {
      window.clearInterval(timer)
      ACTIVITY_EVENTS.forEach(name => window.removeEventListener(name, markActive))
      window.removeEventListener("scroll", onScroll)
      document.removeEventListener("visibilitychange", onVisibility)
      window.removeEventListener("pagehide", onPageHide)
      document.removeEventListener("click", onClick, true)
      document.removeEventListener("auxclick", onClick, true)
    }
  }, [])

  useEffect(() => {
    const s = state.current
    // StrictMode runs effects twice in development; count each path once.
    if (!pathname || pathname === s.path || navigator.webdriver) return
    flushEngagement(s)
    s.path = pathname
    if (pathname.startsWith("/admin")) {
      s.pv = null
      return
    }

    s.pv = newPageViewId()
    s.seconds = 0
    s.sentSeconds = 0
    s.sentScroll = 0
    s.scroll = scrollPercent()
    s.lastActive = Date.now()
    send({
      type: "pageview",
      pv: s.pv,
      path: pathname,
      referrer: s.isFirstView ? document.referrer : "",
      utm: s.isFirstView ? readUtm() : undefined,
    })
    s.isFirstView = false
  }, [pathname])

  return null
}
