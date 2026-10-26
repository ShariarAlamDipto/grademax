"use client"
import { useEffect } from "react"

/**
 * After a deploy, a tab that was open before it still points at the previous
 * build's JavaScript chunks, which no longer exist; the next client-side
 * navigation then fails with ChunkLoadError and the page breaks. Seen live in
 * Admin → Analytics → Performance (26 Oct 2026). Reloading fetches the new
 * build. A sessionStorage stamp allows one reload per minute, so a chunk that
 * is genuinely missing cannot cause a reload loop.
 */
const STAMP = "gm_chunk_reload"
const MIN_GAP_MS = 60_000
const CHUNK_ERROR = /ChunkLoadError|Loading chunk [\w-]+ failed|Failed to load chunk|Failed to fetch dynamically imported module/i

function reloadOnce(): void {
  try {
    const last = Number(window.sessionStorage.getItem(STAMP) ?? 0)
    if (Date.now() - last < MIN_GAP_MS) return
    window.sessionStorage.setItem(STAMP, String(Date.now()))
  } catch {
    return // no storage: do not risk a loop
  }
  window.location.reload()
}

export default function ChunkReloadGuard() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => { if (CHUNK_ERROR.test(event.message ?? "")) reloadOnce() }
    const onRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason instanceof Error ? `${event.reason.name}: ${event.reason.message}` : String(event.reason ?? "")
      if (CHUNK_ERROR.test(reason)) reloadOnce()
    }
    window.addEventListener("error", onError)
    window.addEventListener("unhandledrejection", onRejection)
    return () => {
      window.removeEventListener("error", onError)
      window.removeEventListener("unhandledrejection", onRejection)
    }
  }, [])
  return null
}
