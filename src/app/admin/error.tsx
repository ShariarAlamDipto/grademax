"use client"

import { useEffect } from "react"
import Link from "next/link"

/**
 * Shown when anything in the admin area throws, instead of an empty page under
 * the navbar. In production Next.js hides server error messages, so the digest
 * is what matches this screen to the server log line.
 */
export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("[admin] render failed:", error)
  }, [error])

  return (
    <main style={{ maxWidth: "40rem", margin: "0 auto", padding: "4rem 1.25rem", color: "var(--gm-text)" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "0.5rem" }}>The admin portal could not load</h1>
      <p style={{ color: "var(--gm-text-2)", lineHeight: 1.6, marginBottom: "1rem" }}>
        Something failed while loading this admin page. Try again; if it keeps happening, send the details below.
      </p>
      <pre style={{
        whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: "0.8rem", lineHeight: 1.5,
        padding: "0.9rem 1rem", borderRadius: "0.75rem", border: "1px solid var(--gm-border-2)",
        background: "var(--gm-surface)", color: "var(--gm-text)", marginBottom: "1.25rem",
      }}>
        {error.message || "No message"}
        {error.digest ? `\nDigest: ${error.digest}` : ""}
      </pre>
      <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={reset}
          style={{ padding: "0.6rem 1.1rem", borderRadius: "0.6rem", border: "1px solid var(--gm-border-2)", background: "var(--gm-text)", color: "var(--gm-bg)", fontWeight: 600, cursor: "pointer" }}
        >
          Try again
        </button>
        <Link href="/" style={{ padding: "0.6rem 1.1rem", borderRadius: "0.6rem", border: "1px solid var(--gm-border-2)", color: "var(--gm-text)", textDecoration: "none", fontWeight: 600 }}>
          Back to site
        </Link>
      </div>
    </main>
  )
}
