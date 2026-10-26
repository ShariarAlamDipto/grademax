"use client"
import { useEffect, useRef, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import { classifyLinkClick } from "@/lib/siteBehavior"
import { COUNTER_KEY, DOWNLOAD_LIMIT, decideDownload, readCounter } from "@/lib/downloadGate"
import { sendVisitBeacon } from "@/lib/visitBeacon"

/**
 * Free sign-in after DOWNLOAD_LIMIT PDF downloads a day (see downloadGate.ts).
 *
 * Every PDF link on the site (paper pages, paper lists, the viewer's Open
 * button) is a plain link to the file, so one click listener covers them all.
 * It listens on window in the capture phase, before the analytics tracker's
 * document listener, so a stopped click is not also counted as a download.
 */
export default function DownloadGate() {
  const [open, setOpen] = useState(false)
  const auth = useRef({ known: false, signedIn: false })
  const signInRef = useRef<HTMLAnchorElement>(null)

  // Session from local storage: no network request, so it is known almost at once.
  useEffect(() => {
    let active = true
    supabase.auth.getSession()
      .then(({ data }) => { if (active) auth.current = { known: true, signedIn: !!data.session } })
      .catch(() => { /* stays unknown: downloads are allowed */ })
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      auth.current = { known: true, signedIn: !!session }
      if (session) setOpen(false)
    })
    return () => { active = false; listener.subscription.unsubscribe() }
  }, [])

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (event.button > 1) return
      const link = (event.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null
      if (!link || classifyLinkClick(link.href, window.location.hostname)?.name !== "download") return

      let raw: string | null
      try { raw = window.localStorage.getItem(COUNTER_KEY) } catch { return } // no storage: never block
      const today = new Date().toLocaleDateString("en-CA")
      const decision = decideDownload({ signedIn: auth.current.signedIn, authKnown: auth.current.known, counter: readCounter(raw, today) })
      if (decision.allow) {
        try { window.localStorage.setItem(COUNTER_KEY, JSON.stringify(decision.counter)) } catch { /* ignore */ }
        return
      }
      event.preventDefault()
      event.stopPropagation()
      setOpen(true)
      const gpc = (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true
      if (!gpc) sendVisitBeacon({ type: "event", name: "gate_shown", label: `downloads:${decision.counter.count}`, path: window.location.pathname })
    }
    window.addEventListener("click", onClick, true)
    window.addEventListener("auxclick", onClick, true)
    return () => {
      window.removeEventListener("click", onClick, true)
      window.removeEventListener("auxclick", onClick, true)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    signInRef.current?.focus()
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false) }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])

  if (!open) return null
  const next = typeof window === "undefined" ? "/" : `${window.location.pathname}${window.location.search}`

  return (
    <div
      onClick={() => setOpen(false)}
      style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0, 0, 0, 0.55)", display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="download-gate-title"
        onClick={event => event.stopPropagation()}
        style={{ width: "100%", maxWidth: "420px", background: "var(--gm-surface)", border: "1px solid var(--gm-border)", borderRadius: "1rem", padding: "1.5rem", boxShadow: "0 20px 60px rgba(0,0,0,0.4)" }}
      >
        <h2 id="download-gate-title" style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--gm-text)", marginBottom: "0.5rem" }}>
          Sign in to keep downloading
        </h2>
        <p style={{ fontSize: "0.9rem", color: "var(--gm-text-2)", lineHeight: 1.55, marginBottom: "1.25rem" }}>
          You have downloaded {DOWNLOAD_LIMIT} papers today. Signing in is free and gives you unlimited downloads,
          plus the worksheet generator and test builder.
        </p>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <a
            ref={signInRef}
            href={`/login?next=${encodeURIComponent(next)}`}
            style={{ flex: "1 1 auto", textAlign: "center", padding: "0.7rem 1rem", borderRadius: "0.6rem", background: "var(--gm-blue)", color: "#fff", fontWeight: 700, fontSize: "0.9rem", textDecoration: "none" }}
          >
            Sign in free
          </a>
          <button
            onClick={() => setOpen(false)}
            style={{ flex: "0 0 auto", padding: "0.7rem 1rem", borderRadius: "0.6rem", background: "transparent", border: "1px solid var(--gm-border)", color: "var(--gm-text-2)", fontSize: "0.9rem", cursor: "pointer" }}
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  )
}
