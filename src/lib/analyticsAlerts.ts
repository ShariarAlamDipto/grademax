import type { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/**
 * Analytics alerts to the shop's Telegram chat (the order bot, migration 40).
 *
 * analytics_alert_check() decides what is worth sending: thresholds, at most
 * one evaluation per 15 minutes and one message per rule per 6 hours. This
 * only delivers what it returns. Never throws: it runs after a response.
 */
type Db = NonNullable<ReturnType<typeof getSupabaseAdmin>>

const TELEGRAM_TIMEOUT_MS = 4000

interface Alert { rule: string; message: string }

export async function runAnalyticsAlerts(db: Db): Promise<void> {
  const token = process.env.TELEGRAM_BOT_TOKEN?.trim()
  const chatId = process.env.TELEGRAM_CHAT_ID?.trim()
  if (!token || !chatId) return

  try {
    const { data, error } = await db.rpc("analytics_alert_check")
    if (error) {
      // PGRST202: migration 40 not applied yet.
      if (error.code !== "PGRST202") console.error(`[analytics-alerts] check failed (${error.code ?? "no code"}): ${error.message}`)
      return
    }
    for (const alert of (Array.isArray(data) ? data : []) as Alert[]) {
      const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Plain text: the messages contain counts and fixed wording only.
        body: JSON.stringify({ chat_id: chatId, text: `⚠️ GradeMax alert\n${alert.message}`, disable_web_page_preview: true }),
        signal: AbortSignal.timeout(TELEGRAM_TIMEOUT_MS),
      })
      if (!response.ok) console.error(`[analytics-alerts] Telegram refused ${alert.rule} (${response.status})`)
    }
  } catch (error: unknown) {
    console.error("[analytics-alerts] failed:", error instanceof Error ? error.message : error)
  }
}
