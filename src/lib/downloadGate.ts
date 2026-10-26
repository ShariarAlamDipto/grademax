/**
 * Free sign-in after heavy downloading (decided 26 Oct 2026).
 *
 * Signed-out visitors can download DOWNLOAD_LIMIT PDFs a day; the next one
 * asks them to sign in, which is free and unlocks unlimited downloads. Nobody
 * is blocked from studying. It is a soft gate: the count lives in the browser
 * and the PDF addresses stay public, so it stops casual bulk downloading, not
 * a determined scraper. The pure rules live here; the UI is DownloadGate.tsx.
 */

export const DOWNLOAD_LIMIT = 20
export const COUNTER_KEY = "gm_downloads"

export interface Counter {
  day: string
  count: number
}

/** Today's counter from localStorage text; anything unreadable starts at 0. */
export function readCounter(raw: string | null, today: string): Counter {
  try {
    const parsed = raw ? JSON.parse(raw) : null
    if (parsed?.day === today && Number.isInteger(parsed.count) && parsed.count >= 0) {
      return { day: today, count: parsed.count }
    }
  } catch {
    // fall through
  }
  return { day: today, count: 0 }
}

/**
 * Whether a download may go ahead, and the counter to store afterwards.
 * Signed-in students are never limited. While sign-in status is still
 * unknown (first moments of a page load) the download is allowed rather than
 * risking a false prompt.
 */
export function decideDownload(input: { signedIn: boolean; authKnown: boolean; counter: Counter }): { allow: boolean; counter: Counter } {
  const { signedIn, authKnown, counter } = input
  if (signedIn || !authKnown) return { allow: true, counter }
  if (counter.count >= DOWNLOAD_LIMIT) return { allow: false, counter }
  return { allow: true, counter: { day: counter.day, count: counter.count + 1 } }
}
