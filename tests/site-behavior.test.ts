import { test } from "node:test"
import assert from "node:assert/strict"
import {
  classifyChannel,
  parseBrowser,
  parseOs,
  sanitizeUtm,
  parseBeacon,
  classifyLinkClick,
  sanitizeErrorLabel,
} from "../src/lib/siteBehavior"

const UA = {
  chromeWin: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
  edge: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36 Edg/120.0",
  safariMac: "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
  safariIphone: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
  chromeIphone: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 CriOS/120.0 Mobile/15E148 Safari/604.1",
  samsung: "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 SamsungBrowser/23.0 Chrome/115.0 Mobile Safari/537.36",
  firefox: "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
  fbApp: "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/119.0 Mobile Safari/537.36 [FBAN/EMA;FBLC/en_US;FBAV/400.0]",
  opera: "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120.0 Safari/537.36 OPR/105.0",
  chromebook: "Mozilla/5.0 (X11; CrOS x86_64 15633.69.0) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
}

test("parseBrowser names the common browsers and in-app browsers", () => {
  assert.equal(parseBrowser(UA.chromeWin), "Chrome")
  assert.equal(parseBrowser(UA.edge), "Edge")
  assert.equal(parseBrowser(UA.safariMac), "Safari")
  assert.equal(parseBrowser(UA.safariIphone), "Safari")
  assert.equal(parseBrowser(UA.chromeIphone), "Chrome")
  assert.equal(parseBrowser(UA.samsung), "Samsung Internet")
  assert.equal(parseBrowser(UA.firefox), "Firefox")
  assert.equal(parseBrowser(UA.fbApp), "Facebook app")
  assert.equal(parseBrowser(UA.opera), "Opera")
  assert.equal(parseBrowser("something odd"), "Other")
})

test("parseOs names the operating system", () => {
  assert.equal(parseOs(UA.chromeWin), "Windows")
  assert.equal(parseOs(UA.safariMac), "macOS")
  assert.equal(parseOs(UA.safariIphone), "iOS")
  assert.equal(parseOs(UA.samsung), "Android")
  assert.equal(parseOs(UA.firefox), "Linux")
  assert.equal(parseOs(UA.chromebook), "ChromeOS")
  assert.equal(parseOs("something odd"), "Other")
})

test("sanitizeUtm keeps short plain tags and drops the rest", () => {
  assert.equal(sanitizeUtm("Facebook"), "facebook")
  assert.equal(sanitizeUtm("  spring_sale-2026 "), "spring_sale-2026")
  assert.equal(sanitizeUtm("<script>"), null)
  assert.equal(sanitizeUtm("a".repeat(101)), null)
  assert.equal(sanitizeUtm(""), null)
  assert.equal(sanitizeUtm(42), null)
})

test("classifyChannel groups traffic sources", () => {
  const none = { source: null, medium: null }
  assert.equal(classifyChannel(null, none), "direct")
  assert.equal(classifyChannel("google.com", none), "search")
  assert.equal(classifyChannel("google.com.bd", none), "search")
  assert.equal(classifyChannel("bing.com", none), "search")
  assert.equal(classifyChannel("duckduckgo.com", none), "search")
  assert.equal(classifyChannel("chatgpt.com", none), "ai")
  assert.equal(classifyChannel("gemini.google.com", none), "ai")
  assert.equal(classifyChannel("perplexity.ai", none), "ai")
  assert.equal(classifyChannel("l.facebook.com", none), "social")
  assert.equal(classifyChannel("m.youtube.com", none), "social")
  assert.equal(classifyChannel("t.co", none), "social")
  assert.equal(classifyChannel("discord.com", none), "social")
  assert.equal(classifyChannel("someblog.example", none), "referral")
  assert.equal(classifyChannel("l.facebook.com", { source: "facebook", medium: "cpc" }), "paid")
  assert.equal(classifyChannel(null, { source: "newsletter", medium: "email" }), "email")
  assert.equal(classifyChannel(null, { source: "facebook", medium: null }), "social")
  assert.equal(classifyChannel(null, { source: "partner-site", medium: null }), "referral")
})

test("parseBeacon validates each beacon type", () => {
  const pv = "3f2b8c1e-9a4d-4e6f-8b2a-1c3d5e7f9a0b"
  assert.deepEqual(parseBeacon({ type: "pageview", pv, path: "/store?x=1", referrer: "https://www.google.com/", utm: { source: "Google", medium: "cpc", campaign: "exam season" } }), {
    type: "pageview", pv, path: "/store", referrer: "https://www.google.com/",
    utm: { source: "google", medium: "cpc", campaign: "exam season" },
  })
  // Older trackers sent no type and no pv.
  assert.deepEqual(parseBeacon({ path: "/" }), { type: "pageview", pv: null, path: "/", referrer: null, utm: { source: null, medium: null, campaign: null } })
  assert.deepEqual(parseBeacon({ type: "engage", pv, seconds: 42.7, scroll: 130 }), { type: "engage", pv, seconds: 42, scroll: 100 })
  assert.deepEqual(parseBeacon({ type: "engage", pv, seconds: -5, scroll: -1 }), { type: "engage", pv, seconds: 0, scroll: 0 })
  assert.equal(parseBeacon({ type: "engage", pv: "nope", seconds: 4, scroll: 4 }), null)
  assert.deepEqual(parseBeacon({ type: "event", name: "download", label: "/papers/x.pdf", path: "/past-papers/physics" }), {
    type: "event", name: "download", label: "/papers/x.pdf", path: "/past-papers/physics",
  })
  assert.equal(parseBeacon({ type: "event", name: "order_placed", label: "x", path: "/" }), null, "server-only events are refused from browsers")
  assert.equal(parseBeacon({ type: "event", name: "download", label: "x".repeat(300), path: "/" })?.type, "event")
  assert.equal((parseBeacon({ type: "event", name: "download", label: "x".repeat(300), path: "/" }) as { label: string }).label.length, 200)
  assert.equal(parseBeacon({ type: "pageview", path: "/admin" }), null)
  assert.equal(parseBeacon(null), null)
  assert.equal(parseBeacon("str"), null)
})

test("parseBeacon accepts Core Web Vitals and JavaScript errors", () => {
  const pv = "3f2b8c1e-9a4d-4e6f-8b2a-1c3d5e7f9a0b"
  assert.deepEqual(parseBeacon({ type: "vital", pv, name: "LCP", value: 2512.7 }), { type: "vital", pv, name: "LCP", value: 2513 })
  assert.deepEqual(parseBeacon({ type: "vital", pv, name: "CLS", value: 0.123 }), { type: "vital", pv, name: "CLS", value: 0.123 })
  assert.equal(parseBeacon({ type: "vital", pv, name: "FID", value: 3 }), null, "only the five current metrics")
  assert.equal(parseBeacon({ type: "vital", pv, name: "LCP", value: -1 }), null)
  assert.equal(parseBeacon({ type: "vital", pv, name: "LCP", value: 9e9 }), null, "absurd values are dropped")
  assert.equal(parseBeacon({ type: "vital", pv: "x", name: "LCP", value: 1 }), null)
  assert.equal((parseBeacon({ type: "event", name: "js_error", label: "TypeError: x is undefined @ /_next/app.js:1", path: "/store" }) as { name: string }).name, "js_error")
  assert.equal((parseBeacon({ type: "event", name: "gate_shown", label: "downloads:20", path: "/past-papers/physics" }) as { name: string }).name, "gate_shown")
})

test("sanitizeErrorLabel keeps the useful part of an error and drops noise", () => {
  assert.equal(sanitizeErrorLabel("TypeError: Cannot read properties of null", "https://www.grademax.me/_next/static/chunks/app.js?v=1", 12),
    "TypeError: Cannot read properties of null @ /_next/static/chunks/app.js:12")
  assert.equal(sanitizeErrorLabel("Error at https://x.example/a?token=secret&b=1", "", 0), "Error at https://x.example/a")
  assert.equal(sanitizeErrorLabel("Script error.", "", 0), null, "cross-origin errors carry no information")
  assert.equal(sanitizeErrorLabel("ResizeObserver loop limit exceeded", "", 0), null)
  assert.equal(sanitizeErrorLabel("TypeError: undefined is not an object (evaluating 'window.__firefox__.reader')", "https://www.grademax.me/past-papers", 1), null, "Firefox iOS injected script")
  assert.equal(sanitizeErrorLabel("ReferenceError: Can't find variable: __gCrWeb", "", 0), null, "Chrome iOS injected script")
  assert.ok(sanitizeErrorLabel("ChunkLoadError: Failed to load chunk /_next/static/chunks/a.js", "", 0), "real errors are kept")
  assert.equal(sanitizeErrorLabel("boom", "chrome-extension://abc/x.js", 3), null, "browser extensions are not our bugs")
  assert.equal(sanitizeErrorLabel("x".repeat(500), "", 0)!.length, 200)
})

test("classifyLinkClick spots PDF downloads and outbound links", () => {
  const here = "www.grademax.me"
  assert.deepEqual(classifyLinkClick("https://pub-abc.r2.dev/papers/4PH1/2024/qp.pdf", here), { name: "download", label: "/papers/4PH1/2024/qp.pdf" })
  assert.deepEqual(classifyLinkClick("https://www.grademax.me/files/book.pdf", here), { name: "download", label: "/files/book.pdf" })
  assert.deepEqual(classifyLinkClick("https://discord.gg/abc", here), { name: "outbound", label: "discord.gg" })
  assert.deepEqual(classifyLinkClick("https://www.facebook.com/grademax", here), { name: "outbound", label: "facebook.com" })
  assert.equal(classifyLinkClick("https://www.grademax.me/store", here), null)
  assert.equal(classifyLinkClick("mailto:hi@grademax.me", here), null)
  assert.equal(classifyLinkClick("javascript:void(0)", here), null)
  assert.equal(classifyLinkClick("not a url", here), null)
})
