/**
 * Display helpers for money, phone numbers and dates.
 *
 * Dates render in Asia/Dhaka explicitly. The server runs in UTC, and a daily
 * order count bucketed by UTC would move orders placed after 6pm Dhaka time
 * into the following day — which would quietly corrupt the admin reporting.
 */

export const DHAKA_TZ = "Asia/Dhaka"

/** "৳1,200" — the amount is already an integer number of Taka. */
export function formatBdt(amount: number): string {
  return `৳${amount.toLocaleString("en-US")}`
}

/** "1,200 BDT" for contexts where the symbol renders poorly. */
export function formatBdtPlain(amount: number): string {
  return `${amount.toLocaleString("en-US")} BDT`
}

/** "01712 345678" — easier to read back against a payment app than 11 digits. */
export function formatPhone(msisdn: string): string {
  if (!/^01\d{9}$/.test(msisdn)) return msisdn
  return `${msisdn.slice(0, 5)} ${msisdn.slice(5)}`
}

/** Hide the middle of a phone number for the public order-tracking page. */
export function maskPhone(msisdn: string): string {
  if (msisdn.length < 7) return "•".repeat(msisdn.length)
  return `${msisdn.slice(0, 3)}${"•".repeat(msisdn.length - 5)}${msisdn.slice(-2)}`
}

export function formatDhakaDate(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso
  return d.toLocaleString("en-GB", {
    timeZone: DHAKA_TZ,
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: true,
  })
}

export function formatDhakaDay(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso
  return d.toLocaleDateString("en-GB", {
    timeZone: DHAKA_TZ, day: "2-digit", month: "short", year: "numeric",
  })
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return ""
  const mb = bytes / (1024 * 1024)
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${Math.round(mb)} MB`
}
