import { test } from "node:test"
import assert from "node:assert/strict"
import {
  classifyDevice,
  isBotUserAgent,
  sanitizeVisitPath,
  externalReferrerHost,
  parseCountry,
  hasSupabaseSession,
  isVisitorId,
  isAllowedOrigin,
  createHitCounter,
} from "../src/lib/siteVisits"

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
const ANDROID_PHONE = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"
const ANDROID_TABLET = "Mozilla/5.0 (Linux; Android 13; SM-X700) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
const IPAD = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
const WINDOWS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

test("classifyDevice tells phones, tablets and desktops apart", () => {
  assert.equal(classifyDevice(IPHONE), "mobile")
  assert.equal(classifyDevice(ANDROID_PHONE), "mobile")
  assert.equal(classifyDevice(ANDROID_TABLET), "tablet")
  assert.equal(classifyDevice(IPAD), "tablet")
  assert.equal(classifyDevice(WINDOWS), "desktop")
  assert.equal(classifyDevice(""), "desktop")
})

test("isBotUserAgent catches crawlers, scripts and empty agents", () => {
  assert.equal(isBotUserAgent("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"), true)
  assert.equal(isBotUserAgent("curl/8.4.0"), true)
  assert.equal(isBotUserAgent("Mozilla/5.0 HeadlessChrome/120.0"), true)
  assert.equal(isBotUserAgent(""), true)
  assert.equal(isBotUserAgent(WINDOWS), false)
  assert.equal(isBotUserAgent(IPHONE), false)
})

test("sanitizeVisitPath keeps public paths and rejects the rest", () => {
  assert.equal(sanitizeVisitPath("/past-papers/physics"), "/past-papers/physics")
  assert.equal(sanitizeVisitPath("/"), "/")
  assert.equal(sanitizeVisitPath("/store?ref=fb#top"), "/store")
  assert.equal(sanitizeVisitPath("/admin/analytics"), null)
  assert.equal(sanitizeVisitPath("/api/visit"), null)
  assert.equal(sanitizeVisitPath("https://evil.example/x"), null)
  assert.equal(sanitizeVisitPath("//evil.example"), null)
  assert.equal(sanitizeVisitPath(""), null)
  assert.equal(sanitizeVisitPath(42), null)
  assert.equal(sanitizeVisitPath("/" + "a".repeat(400)), null)
  assert.equal(sanitizeVisitPath("/<script>alert(1)</script> x"), null)
  assert.equal(sanitizeVisitPath("/past papers"), null)
  assert.equal(sanitizeVisitPath("/caf%C3%A9"), "/caf%C3%A9")
})

test("isAllowedOrigin accepts only GradeMax pages (and localhost outside production)", () => {
  assert.equal(isAllowedOrigin("https://www.grademax.me", true), true)
  assert.equal(isAllowedOrigin("https://grademax.me", true), true)
  assert.equal(isAllowedOrigin("https://evil.example", true), false)
  assert.equal(isAllowedOrigin("https://www.grademax.me.evil.example", true), false)
  assert.equal(isAllowedOrigin(null, true), false)
  assert.equal(isAllowedOrigin("null", true), false)
  assert.equal(isAllowedOrigin("http://localhost:3000", true), false)
  assert.equal(isAllowedOrigin("http://localhost:3000", false), true)
})

test("createHitCounter caps hits per key within a window", () => {
  let now = 0
  const counter = createHitCounter({ limit: 3, windowMs: 1000, maxKeys: 2, now: () => now })
  assert.deepEqual([1, 2, 3, 4].map(() => counter.hit("a")), [true, true, true, false])
  assert.equal(counter.hit("b"), true)
  now = 1001
  assert.equal(counter.hit("a"), true, "window resets")
  // A flood of new keys never grows memory past maxKeys.
  for (let i = 0; i < 100; i++) counter.hit(`k${i}`)
  assert.ok(counter.size() <= 2)
})

test("externalReferrerHost keeps only other sites' host names", () => {
  assert.equal(externalReferrerHost("https://www.google.com/search?q=grademax"), "google.com")
  assert.equal(externalReferrerHost("https://l.facebook.com/l.php?u=x"), "l.facebook.com")
  assert.equal(externalReferrerHost("https://www.grademax.me/past-papers"), null)
  assert.equal(externalReferrerHost("https://grademax.me/"), null)
  assert.equal(externalReferrerHost(""), null)
  assert.equal(externalReferrerHost("not a url"), null)
  assert.equal(externalReferrerHost(undefined), null)
})

test("parseCountry accepts two-letter codes only", () => {
  assert.equal(parseCountry("BD"), "BD")
  assert.equal(parseCountry("gb"), "GB")
  assert.equal(parseCountry("XX"), null)
  assert.equal(parseCountry("T1"), null)
  assert.equal(parseCountry(null), null)
  assert.equal(parseCountry("BDX"), null)
})

test("hasSupabaseSession looks for the auth-token cookie", () => {
  assert.equal(hasSupabaseSession(["gm_vid", "sb-abcd-auth-token.0"]), true)
  assert.equal(hasSupabaseSession(["sb-abcd-auth-token"]), true)
  assert.equal(hasSupabaseSession(["gm_vid", "theme"]), false)
})

test("isVisitorId accepts only UUIDs", () => {
  assert.equal(isVisitorId("3f2b8c1e-9a4d-4e6f-8b2a-1c3d5e7f9a0b"), true)
  assert.equal(isVisitorId("'; drop table site_visits; --"), false)
  assert.equal(isVisitorId(undefined), false)
})
