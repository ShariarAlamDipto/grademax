import { test } from "node:test"
import assert from "node:assert/strict"
import { publicOrigin } from "../src/lib/safeRedirect"

const req = (url: string, headers: Record<string, string> = {}) => new Request(url, { headers })

test("a self-hosted server's bind address is replaced by the public site", () => {
  // `next start` / standalone with HOSTNAME=0.0.0.0 builds request.url from the bind address
  assert.equal(publicOrigin(req("https://0.0.0.0:3000/auth/callback")), "https://www.grademax.me")
  assert.equal(
    publicOrigin(req("http://0.0.0.0:3000/auth/callback", { host: "0.0.0.0:3000" })),
    "https://www.grademax.me"
  )
})

test("the forwarded GradeMax host is kept", () => {
  assert.equal(
    publicOrigin(req("https://0.0.0.0:3000/x", { "x-forwarded-host": "www.grademax.me" })),
    "https://www.grademax.me"
  )
  assert.equal(
    publicOrigin(req("https://0.0.0.0:3000/x", { "x-forwarded-host": "grademax.me", "x-forwarded-proto": "https" })),
    "https://grademax.me"
  )
  assert.equal(publicOrigin(req("https://www.grademax.me/auth/callback")), "https://www.grademax.me")
})

test("a forged host header cannot redirect users off GradeMax", () => {
  assert.equal(
    publicOrigin(req("https://0.0.0.0:3000/x", { "x-forwarded-host": "evil.com" })),
    "https://www.grademax.me"
  )
  assert.equal(
    publicOrigin(req("https://0.0.0.0:3000/x", { "x-forwarded-host": "www.grademax.me.evil.com" })),
    "https://www.grademax.me"
  )
  assert.equal(publicOrigin(req("https://evil.com/x", { host: "evil.com" })), "https://www.grademax.me")
})

test("production hosts are always https, even if the proxy says http", () => {
  assert.equal(
    publicOrigin(req("http://0.0.0.0:3000/x", { "x-forwarded-host": "www.grademax.me", "x-forwarded-proto": "http" })),
    "https://www.grademax.me"
  )
})

test("local development keeps its own origin", () => {
  assert.equal(publicOrigin(req("http://localhost:3000/auth/callback")), "http://localhost:3000")
  assert.equal(publicOrigin(req("http://127.0.0.1:3001/auth/callback")), "http://127.0.0.1:3001")
})
