"use client"

import { useState } from "react"
import { Button, Field, Notice } from "./StoreUI"
import { formatBdt } from "@/lib/store/format"
import type { PaymentMethod } from "@/lib/store/types"

/**
 * "I have paid" — the buyer reports a bKash or Nagad transaction.
 *
 * Used both immediately after checkout and later from the order tracking page,
 * because a buyer who closes the tab before paying must be able to come back and
 * finish. Both places need identical validation and wording, so they share this.
 */

interface Props {
  orderNumber: string
  totalBdt: number
  method: Exclude<PaymentMethod, "cod">
  /** The wallet number to send to. Null when none is configured yet. */
  payTo: string | null
  instructions?: string
  onSubmitted?: () => void
}

const MIN_TRANSACTION_ID = 4
const MIN_PHONE = 6

export default function PaymentClaimForm({
  orderNumber, totalBdt, method, payTo, instructions, onSubmitted,
}: Props) {
  const [transactionId, setTransactionId] = useState("")
  const [sender, setSender] = useState("")
  const [state, setState] = useState<"idle" | "sending" | "done">("idle")
  const [error, setError] = useState<string | null>(null)

  const methodName = method === "bkash" ? "bKash" : "Nagad"
  const ready =
    transactionId.trim().length >= MIN_TRANSACTION_ID && sender.trim().length >= MIN_PHONE

  async function submit() {
    setError(null)
    setState("sending")
    try {
      const res = await fetch("/api/store/payment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          orderNumber,
          phone: sender,
          method,
          senderMsisdn: sender,
          transactionId: transactionId.trim(),
          amountBdt: totalBdt,
        }),
      })
      const json = await res.json()
      if (!res.ok) {
        setError(json.error ?? "We could not record your payment. Please try again.")
        setState("idle")
        return
      }
      setState("done")
      onSubmitted?.()
    } catch {
      setError("We could not reach the server. Please check your connection and try again.")
      setState("idle")
    }
  }

  if (state === "done") {
    return <Notice tone="green">Payment recorded. We are checking it now.</Notice>
  }

  return (
    <>
      {payTo ? (
        <div style={{
          background: "var(--gm-surface-2)", border: "1px solid var(--gm-border-2)",
          borderRadius: "0.6rem", padding: "0.9rem", margin: "0 0 0.9rem",
        }}>
          <span style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", display: "block" }}>
            Send {formatBdt(totalBdt)} with {methodName} to
          </span>
          <strong style={{ fontSize: "1.2rem", fontWeight: 800, letterSpacing: "0.02em" }}>
            {payTo}
          </strong>
        </div>
      ) : (
        <Notice tone="red">
          No {methodName} number is set up yet. Please contact us with your order number
          ({orderNumber}) and we will take it from there.
        </Notice>
      )}

      {instructions ? (
        <p style={{ fontSize: "0.82rem", color: "var(--gm-text-2)", lineHeight: 1.6, marginBottom: "1rem" }}>
          {instructions}
        </p>
      ) : null}

      {error ? <Notice tone="red">{error}</Notice> : null}

      <Field label="The number you sent from" required>
        <input
          className="gm-input" value={sender} onChange={e => setSender(e.target.value)}
          inputMode="tel" autoComplete="tel" placeholder="01712345678"
        />
      </Field>

      <Field
        label="Transaction ID"
        required
        hint={`On the confirmation message from ${methodName} — letters and numbers only.`}
      >
        <input
          className="gm-input"
          value={transactionId}
          onChange={e => setTransactionId(e.target.value.toUpperCase())}
          placeholder="e.g. 8N7A2K9QX1"
          autoComplete="off"
          spellCheck={false}
          style={{ letterSpacing: "0.05em" }}
        />
      </Field>

      <Button full onClick={submit} disabled={state === "sending" || !ready}>
        {state === "sending" ? "Recording…" : "I have paid"}
      </Button>
    </>
  )
}
