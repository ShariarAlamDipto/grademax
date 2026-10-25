"use client"
import { usePathname } from "next/navigation"
import { useEffect, useRef } from "react"

/**
 * Sends one anonymous page view to /api/visit per navigation, for the admin
 * Visitors dashboard. Only the pathname is sent (never the query string), plus
 * document.referrer on the first page so the dashboard can show where visitors
 * came from.
 */
export default function VisitTracker() {
  const pathname = usePathname()
  const lastPath = useRef<string | null>(null)
  const isFirstView = useRef(true)

  useEffect(() => {
    // StrictMode runs effects twice in development; count each path once.
    if (!pathname || pathname === lastPath.current) return
    lastPath.current = pathname
    if (pathname.startsWith("/admin") || navigator.webdriver) return

    const payload = JSON.stringify({
      path: pathname,
      referrer: isFirstView.current ? document.referrer : "",
    })
    isFirstView.current = false

    try {
      const blob = new Blob([payload], { type: "application/json" })
      if (navigator.sendBeacon?.("/api/visit", blob)) return
    } catch {
      // Fall through to fetch.
    }
    fetch("/api/visit", { method: "POST", body: payload, keepalive: true, headers: { "Content-Type": "application/json" } })
      .catch(() => {})
  }, [pathname])

  return null
}
