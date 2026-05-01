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

  const csp = globalHeaders.headers.find((header) => header.key.toLowerCase() === "content-security-policy");
  assert.ok(csp?.value, "Missing global CSP header");
  assert.match(csp.value, /frame-ancestors 'none'/);
});
