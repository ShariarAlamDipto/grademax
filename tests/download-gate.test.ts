import { test } from "node:test"
import assert from "node:assert/strict"
import { DOWNLOAD_LIMIT, decideDownload, readCounter } from "../src/lib/downloadGate"

const today = "2026-10-26"

test("readCounter starts fresh each day and survives junk", () => {
  assert.deepEqual(readCounter(null, today), { day: today, count: 0 })
  assert.deepEqual(readCounter(JSON.stringify({ day: today, count: 7 }), today), { day: today, count: 7 })
  assert.deepEqual(readCounter(JSON.stringify({ day: "2026-10-25", count: 19 }), today), { day: today, count: 0 }, "yesterday's count resets")
  assert.deepEqual(readCounter("not json", today), { day: today, count: 0 })
  assert.deepEqual(readCounter(JSON.stringify({ day: today, count: -4 }), today), { day: today, count: 0 })
  assert.deepEqual(readCounter(JSON.stringify({ day: today, count: "9" }), today), { day: today, count: 0 })
})

test("signed-in students are never limited and not counted", () => {
  const d = decideDownload({ signedIn: true, authKnown: true, counter: { day: today, count: 500 } })
  assert.deepEqual(d, { allow: true, counter: { day: today, count: 500 } })
})

test("signed-out visitors get the limit, then the sign-in prompt", () => {
  const under = decideDownload({ signedIn: false, authKnown: true, counter: { day: today, count: DOWNLOAD_LIMIT - 1 } })
  assert.deepEqual(under, { allow: true, counter: { day: today, count: DOWNLOAD_LIMIT } })
  const at = decideDownload({ signedIn: false, authKnown: true, counter: { day: today, count: DOWNLOAD_LIMIT } })
  assert.deepEqual(at, { allow: false, counter: { day: today, count: DOWNLOAD_LIMIT } })
})

test("while sign-in status is still unknown the download is allowed (never block a student by mistake)", () => {
  const d = decideDownload({ signedIn: false, authKnown: false, counter: { day: today, count: 99 } })
  assert.equal(d.allow, true)
})

test("the limit is 20 downloads a day", () => {
  assert.equal(DOWNLOAD_LIMIT, 20)
})
