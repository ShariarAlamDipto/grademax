import { test } from "node:test"
import assert from "node:assert/strict"
import { parseAnalyticsQuery, localDate, toCsv } from "../src/lib/analyticsQuery"

const NOW = new Date("2026-10-25T20:30:00Z") // 26 Oct 02:30 in Dhaka (UTC+6)

test("localDate uses the reporting time zone", () => {
  assert.equal(localDate(NOW, "Asia/Dhaka"), "2026-10-26")
  assert.equal(localDate(NOW, "UTC"), "2026-10-25")
})

test("presets become day counts or single local days", () => {
  const p = (q: Record<string, string>) => parseAnalyticsQuery(new URLSearchParams(q), NOW)
  assert.deepEqual(p({}), { ok: true, range: { days: 30 }, country: null })
  assert.deepEqual(p({ range: "7" }), { ok: true, range: { days: 7 }, country: null })
  assert.deepEqual(p({ range: "90" }), { ok: true, range: { days: 90 }, country: null })
  assert.deepEqual(p({ range: "today" }), { ok: true, range: { from: "2026-10-26", to: "2026-10-26" }, country: null })
  assert.deepEqual(p({ range: "yesterday" }), { ok: true, range: { from: "2026-10-25", to: "2026-10-25" }, country: null })
  // The old ?days= parameter still works.
  assert.deepEqual(p({ days: "7" }), { ok: true, range: { days: 7 }, country: null })
})

test("custom ranges are validated", () => {
  const p = (q: Record<string, string>) => parseAnalyticsQuery(new URLSearchParams({ range: "custom", ...q }), NOW)
  assert.deepEqual(p({ from: "2026-10-01", to: "2026-10-10" }), { ok: true, range: { from: "2026-10-01", to: "2026-10-10" }, country: null })
  assert.equal(p({ from: "2026-10-10", to: "2026-10-01" }).ok, false, "end before start")
  assert.equal(p({ from: "2026-02-30", to: "2026-03-01" }).ok, false, "not a real date")
  assert.equal(p({ from: "2024-01-01", to: "2026-01-01" }).ok, false, "longer than a year")
  assert.equal(p({ from: "1 Oct", to: "2026-10-10" }).ok, false, "wrong format")
  assert.equal(p({ from: "2026-10-01" }).ok, false, "missing end")
  assert.equal(p({ from: "2026-10-01", to: "2027-01-01" }).ok, false, "ends in the future")
})

test("country must be an ISO code or ?? for unknown", () => {
  const p = (country: string) => parseAnalyticsQuery(new URLSearchParams({ country }), NOW)
  assert.deepEqual(p("BD"), { ok: true, range: { days: 30 }, country: "BD" })
  assert.deepEqual(p("??"), { ok: true, range: { days: 30 }, country: "??" })
  assert.deepEqual(p(""), { ok: true, range: { days: 30 }, country: null })
  assert.equal(p("bd").ok, false)
  assert.equal(p("BDX").ok, false)
  assert.equal(p("'; drop").ok, false)
})

test("toCsv quotes values and defuses spreadsheet formulas", () => {
  const csv = toCsv(["Page", "Views"], [["/a,b", 3], ['say "hi"', 4], ["=HYPERLINK(\"x\")", 5], ["-1+2", 6], [null, 7]])
  assert.equal(csv, [
    "Page,Views",
    "\"/a,b\",3",
    "\"say \"\"hi\"\"\",4",
    "\"'=HYPERLINK(\"\"x\"\")\",5",
    "'-1+2,6",
    ",7",
  ].join("\r\n"))
})
