import { test } from "node:test"
import assert from "node:assert/strict"
import { isJsonObject, isUsageReport, readJsonObject, toReportResult } from "../src/lib/adminReportGuards"

const response = (body: () => unknown) => ({ json: async () => body() })

test("isJsonObject accepts only plain objects", () => {
  assert.equal(isJsonObject({}), true)
  assert.equal(isJsonObject({ a: 1 }), true)
  for (const value of [null, undefined, [], [1], "x", 1, true]) assert.equal(isJsonObject(value), false)
})

test("readJsonObject returns the object body", async () => {
  assert.deepEqual(await readJsonObject(response(() => ({ rows: [] }))), { rows: [] })
})

test("readJsonObject returns null for a body that is not a JSON object", async () => {
  // An HTML login or Cloudflare page: res.json() rejects.
  assert.equal(await readJsonObject(response(() => { throw new SyntaxError("Unexpected token <") })), null)
  assert.equal(await readJsonObject(response(() => [])), null)
  assert.equal(await readJsonObject(response(() => null)), null)
  assert.equal(await readJsonObject(response(() => "text")), null)
})

test("toReportResult passes a 2xx object without an error field", () => {
  const body = { totals: { visitors: 3 } }
  assert.deepEqual(toReportResult({ ok: true }, body, "fallback"), { ok: true, data: body })
})

test("toReportResult rejects an error status and keeps the server's message", () => {
  assert.deepEqual(toReportResult({ ok: false }, { error: "This report took too long to load." }, "fallback"),
    { ok: false, error: "This report took too long to load." })
})

test("toReportResult rejects a 200 that carries an error body", () => {
  assert.deepEqual(toReportResult({ ok: true }, { error: "x", notSetUp: true }, "fallback"), { ok: false, error: "x" })
})

test("toReportResult uses the fallback when there is no usable message", () => {
  assert.deepEqual(toReportResult({ ok: true }, null, "fallback"), { ok: false, error: "fallback" })
  assert.deepEqual(toReportResult({ ok: false }, null, "fallback"), { ok: false, error: "fallback" })
  assert.deepEqual(toReportResult({ ok: false }, { error: 42 }, "fallback"), { ok: false, error: "fallback" })
  assert.deepEqual(toReportResult({ ok: false }, { error: "" }, "fallback"), { ok: false, error: "fallback" })
})

test("toReportResult treats an empty object as data (a report with nothing in it is the panel's concern)", () => {
  assert.deepEqual(toReportResult({ ok: true }, {}, "fallback"), { ok: true, data: {} })
})

test("isUsageReport needs every part the usage tab reads unguarded", () => {
  const full = { totals: {}, uniqueUsers: {}, worksheetBySubject: {}, testBuilderBySubject: {}, daily: [] }
  assert.equal(isUsageReport(full), true)
  assert.equal(isUsageReport(null), false)
  assert.equal(isUsageReport({ error: "Admin access required" }), false)
  for (const key of Object.keys(full)) {
    const partial: Record<string, unknown> = { ...full }
    delete partial[key]
    assert.equal(isUsageReport(partial), false, `missing ${key}`)
  }
  assert.equal(isUsageReport({ ...full, daily: {} }), false)
  assert.equal(isUsageReport({ ...full, totals: [] }), false)
})
