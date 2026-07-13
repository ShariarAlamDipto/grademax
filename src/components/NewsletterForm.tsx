"use client"
import { useState } from "react"

export default function NewsletterForm() {
  const [email, setEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [msg, setMsg] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return
    setStatus("loading")
    try {
      const res = await fetch("/api/newsletter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (res.ok) {
        setStatus("success")
        setMsg("You're on the list!")
        setEmail("")
      } else {
        setStatus("error")
        setMsg(data.error || "Something went wrong. Try again.")
      }
    } catch {
      setStatus("error")
      setMsg("Something went wrong. Try again.")
    }
  }

  return (
    <div>
      <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--gm-text)", marginBottom: "0.5rem", letterSpacing: "0.04em" }}>
        Stay updated
      </p>
      <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "0.875rem", lineHeight: 1.5 }}>
        New papers and features, straight to your inbox.
      </p>
      {status === "success" ? (
        <p style={{ fontSize: "0.8rem", color: "#34D399", fontWeight: 600 }}>{msg}</p>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="your@email.com"
            required
            style={{
              width: "100%",
              padding: "0.5rem 0.75rem",
              borderRadius: "0.5rem",
              border: "1px solid var(--gm-border)",
              background: "var(--gm-bg)",
              color: "var(--gm-text)",
              fontSize: "0.8rem",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
          <button
            type="submit"
            disabled={status === "loading"}
            style={{
              padding: "0.5rem 0.75rem",
              borderRadius: "0.5rem",
              background: "#F59E0B",
              color: "#000",
              fontWeight: 700,
              fontSize: "0.8rem",
              border: "none",
              cursor: status === "loading" ? "not-allowed" : "pointer",
              opacity: status === "loading" ? 0.7 : 1,
            }}
          >
            {status === "loading" ? "Subscribing…" : "Subscribe"}
          </button>
          {status === "error" && (
            <p style={{ fontSize: "0.75rem", color: "#f87171" }}>{msg}</p>
          )}
        </form>
      )}
    </div>
  )
}
