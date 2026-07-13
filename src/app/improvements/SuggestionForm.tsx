"use client"
import { useState, FormEvent } from "react"

export default function SuggestionForm() {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle")
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (status === "sending") return
    setStatus("sending")
    setErrorMsg(null)
    try {
      const res = await fetch("/api/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? "Something went wrong")
      }
      setStatus("success")
      setName("")
      setEmail("")
      setMessage("")
    } catch (err) {
      setStatus("error")
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong")
    }
  }

  const inputBase: React.CSSProperties = {
    width: "100%",
    padding: "0.7rem 0.9rem",
    fontSize: "0.9rem",
    background: "var(--gm-bg)",
    color: "var(--gm-text)",
    border: "1px solid var(--gm-border-2)",
    borderRadius: "0.6rem",
    outline: "none",
    fontFamily: "inherit",
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }}>
        <input
          type="text"
          placeholder="Your name (optional)"
          value={name}
          onChange={e => setName(e.target.value)}
          maxLength={120}
          style={inputBase}
          disabled={status === "sending"}
        />
        <input
          type="email"
          placeholder="Your email (optional)"
          value={email}
          onChange={e => setEmail(e.target.value)}
          maxLength={254}
          style={inputBase}
          disabled={status === "sending"}
        />
      </div>

      <textarea
        placeholder="What would you like to see on GradeMax? Be as detailed as you'd like."
        value={message}
        onChange={e => setMessage(e.target.value)}
        required
        minLength={5}
        maxLength={5000}
        rows={7}
        style={{
          ...inputBase,
          resize: "vertical",
          minHeight: "160px",
          lineHeight: 1.6,
        }}
        disabled={status === "sending"}
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", margin: 0 }}>
          {message.length}/5000
        </p>
        <button
          type="submit"
          disabled={status === "sending" || message.trim().length < 5}
          style={{
            padding: "0.65rem 1.6rem",
            fontSize: "0.9rem",
            fontWeight: 700,
            color: "#111",
            background: "var(--gm-amber)",
            border: "none",
            borderRadius: "0.6rem",
            cursor: status === "sending" || message.trim().length < 5 ? "not-allowed" : "pointer",
            opacity: status === "sending" || message.trim().length < 5 ? 0.55 : 1,
            transition: "transform 0.1s ease, opacity 0.15s ease",
          }}
        >
          {status === "sending" ? "Sending…" : "Send suggestion"}
        </button>
      </div>

      {status === "success" && (
        <div style={{
          padding: "0.85rem 1rem",
          borderRadius: "0.6rem",
          background: "rgba(34,197,94,0.10)",
          border: "1px solid rgba(34,197,94,0.35)",
          color: "#22c55e",
          fontSize: "0.85rem",
        }}>
          Thank you — your suggestion has been received. I read every one.
        </div>
      )}

      {status === "error" && (
        <div style={{
          padding: "0.85rem 1rem",
          borderRadius: "0.6rem",
          background: "rgba(239,68,68,0.10)",
          border: "1px solid rgba(239,68,68,0.35)",
          color: "#ef4444",
          fontSize: "0.85rem",
        }}>
          {errorMsg ?? "Couldn't send. Please try again."}
        </div>
      )}
    </form>
  )
}
