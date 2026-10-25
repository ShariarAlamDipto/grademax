/**
 * Query parsing and CSV export for the admin Visitors dashboard.
 *
 * ?range=today|yesterday|7|30|90|custom (&from=YYYY-MM-DD&to=YYYY-MM-DD)
 * &country=BD (ISO code) or ?? (unknown). Days are local to REPORT_TZ, which
 * is also what the database functions use.
 */

export const REPORT_TZ = "Asia/Dhaka"

export type AnalyticsRange = { days: number } | { from: string; to: string }
export type AnalyticsQuery =
  | { ok: true; range: AnalyticsRange; country: string | null }
  | { ok: false; error: string }

const PRESET_DAYS = new Set([7, 30, 90])
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const COUNTRY_RE = /^([A-Z]{2}|\?\?)$/
const MAX_RANGE_DAYS = 366
const DAY_MS = 86_400_000

/** The calendar date (YYYY-MM-DD) of `now` in `timeZone`. */
export function localDate(now: Date, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(now)
}

function shiftDate(isoDate: string, days: number): string {
  return new Date(Date.parse(`${isoDate}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10)
}

function isRealDate(value: string): boolean {
  return DATE_RE.test(value) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value
}

export function parseAnalyticsQuery(params: URLSearchParams, now: Date = new Date()): AnalyticsQuery {
  const countryParam = params.get("country") ?? ""
  if (countryParam && !COUNTRY_RE.test(countryParam)) return { ok: false, error: "Unknown country code." }
  const country = countryParam || null

  const today = localDate(now, REPORT_TZ)
  const range = params.get("range") ?? params.get("days") ?? "30"

  if (range === "today") return { ok: true, range: { from: today, to: today }, country }
  if (range === "yesterday") {
    const day = shiftDate(today, -1)
    return { ok: true, range: { from: day, to: day }, country }
  }
  if (range === "custom") {
    const from = params.get("from") ?? ""
    const to = params.get("to") ?? ""
    if (!isRealDate(from) || !isRealDate(to)) return { ok: false, error: "Choose a start and an end date." }
    if (to < from) return { ok: false, error: "The end date is before the start date." }
    if (to > today) return { ok: false, error: "The end date is in the future." }
    const span = (Date.parse(to) - Date.parse(from)) / DAY_MS + 1
    if (span > MAX_RANGE_DAYS) return { ok: false, error: "Choose a range of one year or less." }
    return { ok: true, range: { from, to }, country }
  }

  const days = Number(range)
  return { ok: true, range: { days: PRESET_DAYS.has(days) ? days : 30 }, country }
}

type CsvValue = string | number | null | undefined

function csvCell(value: CsvValue): string {
  if (value === null || value === undefined) return ""
  let text = String(value)
  // A cell starting with = + - @ (or a tab/CR) runs as a formula in Excel and
  // Sheets. Paths and labels come from visitors, so defuse them.
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function toCsv(headers: string[], rows: CsvValue[][]): string {
  return [headers, ...rows].map(row => row.map(csvCell).join(",")).join("\r\n")
}
