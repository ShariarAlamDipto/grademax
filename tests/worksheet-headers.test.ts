import test from "node:test";
import assert from "node:assert/strict";
import nextConfig from "../next.config";

test("worksheet PDF headers allow same-origin framing", async () => {
  assert.ok(nextConfig.headers, "Expected next.config.ts to export headers()");
  const headers = await nextConfig.headers();
  const worksheetHeaders = headers.find((entry) => entry.source === "/api/worksheets/:path*");

  assert.ok(worksheetHeaders, "Missing worksheet header override");

  const xfo = worksheetHeaders.headers.find((header) => header.key.toLowerCase() === "x-frame-options");
  assert.equal(xfo?.value, "SAMEORIGIN");

  const csp = worksheetHeaders.headers.find((header) => header.key.toLowerCase() === "content-security-policy");
  assert.ok(csp?.value, "Missing CSP header for worksheet endpoint");
  assert.match(csp.value, /frame-ancestors 'self'/);
  assert.match(csp.value, /default-src 'self'/);
});

test("global headers still deny framing", async () => {
  assert.ok(nextConfig.headers, "Expected next.config.ts to export headers()");
  const headers = await nextConfig.headers();
  const globalHeaders = headers.find((entry) => entry.source === "/(.*)");

  assert.ok(globalHeaders, "Missing global header config");

  const xfo = globalHeaders.headers.find((header) => header.key.toLowerCase() === "x-frame-options");
  assert.equal(xfo?.value, "DENY");
});

// The session-cookie responses (OAuth/email callback, password sign-in refresh)
// already carry ~5 KB of Set-Cookie. Adding the ~2.4 KB CSP to them pushed the
// header block past nginx's default proxy buffer, so sign-in returned a 502.
// Those responses are redirects/JSON, so the CSP protects nothing there.
async function cspSourcesMatching(pathname: string): Promise<string[]> {
  assert.ok(nextConfig.headers, "Expected next.config.ts to export headers()");
  const headers = await nextConfig.headers();
  return headers
    .filter((entry) => entry.headers.some((h) => h.key.toLowerCase() === "content-security-policy"))
    .filter((entry) => !entry.source.includes(":")) // param rules are checked separately
    .filter((entry) => new RegExp(`^${entry.source}$`).test(pathname))
    .map((entry) => entry.source);
}

test("pages get the global CSP with frame-ancestors 'none'", async () => {
  for (const path of ["/", "/login", "/dashboard", "/generate", "/past-papers/x/2024/may-jun/paper-1"]) {
    assert.ok((await cspSourcesMatching(path)).length > 0, `Expected CSP on ${path}`);
  }
  const headers = await nextConfig.headers!();
  const pageCsp = headers
    .find((entry) => (entry.headers.some((h) => h.key === "Content-Security-Policy") && new RegExp(`^${entry.source}$`).test("/login")))
    ?.headers.find((h) => h.key === "Content-Security-Policy");
  assert.match(pageCsp?.value ?? "", /frame-ancestors 'none'/);
});

test("session-cookie responses do not carry the CSP", async () => {
  for (const path of ["/auth/callback", "/api/auth/refresh"]) {
    assert.deepEqual(await cspSourcesMatching(path), [], `CSP should not be sent on ${path}`);
  }
});
