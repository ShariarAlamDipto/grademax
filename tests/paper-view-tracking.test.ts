import { test } from "node:test"
import assert from "node:assert/strict"
import { isPrefetch, shouldCountPaperView } from "../src/lib/paperViewTracking"

const VID = "6f1c2b9e-3d4a-4f5b-8c6d-7e8f9a0b1c2d"
const CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
const h = (init: Record<string, string> = {}) => new Headers(init)

test("a browser that the tracker already knows counts", () => {
  assert.equal(shouldCountPaperView({ hasPdf: true, userAgent: CHROME, headers: h(), visitorId: VID }), true)
})

test("no tracker cookie: scrapers with a browser user agent are not counted", () => {
  assert.equal(shouldCountPaperView({ hasPdf: true, userAgent: CHROME, headers: h(), visitorId: undefined }), false)
  assert.equal(shouldCountPaperView({ hasPdf: true, userAgent: CHROME, headers: h(), visitorId: "not-a-uuid" }), false)
})

test("bots, prefetches, opted-out browsers and empty viewers are not counted", () => {
  const base = { hasPdf: true, userAgent: CHROME, headers: h(), visitorId: VID }
  assert.equal(shouldCountPaperView({ ...base, userAgent: "Googlebot/2.1" }), false)
  assert.equal(shouldCountPaperView({ ...base, headers: h({ "next-router-prefetch": "1" }) }), false)
  assert.equal(shouldCountPaperView({ ...base, headers: h({ "sec-gpc": "1" }) }), false)
  assert.equal(shouldCountPaperView({ ...base, hasPdf: false }), false)
})

test("isPrefetch recognises router and speculative prefetches", () => {
  assert.equal(isPrefetch(h({ "next-router-prefetch": "1" })), true)
  assert.equal(isPrefetch(h({ "sec-purpose": "prefetch;prerender" })), true)
  assert.equal(isPrefetch(h({ purpose: "prefetch" })), true)
  assert.equal(isPrefetch(h()), false)
})
