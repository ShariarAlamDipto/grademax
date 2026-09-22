// Free public access to the worksheet generator (/generate) and test builder
// (/test-builder).
//
// This began as a one-month trial from 2026-07-14 with a hardcoded end date,
// which expired on 2026-08-14 and silently put both tools back behind /login.
// Nothing announced that; the tools simply stopped being reachable.
//
// It is now controlled by an environment variable so the window can be opened,
// extended or closed WITHOUT a code change and redeploy:
//
//   PUBLIC_TOOLS_ACCESS_UNTIL unset      -> open (current default)
//   PUBLIC_TOOLS_ACCESS_UNTIL=2026-12-01 -> open until that date, then login
//   PUBLIC_TOOLS_ACCESS_UNTIL=off        -> closed now, login required
//
// The gate is read in three places: src/proxy.ts, src/app/generate/page.tsx and
// src/app/test-builder/page.tsx.

const RAW = process.env.PUBLIC_TOOLS_ACCESS_UNTIL?.trim()

export function isPublicToolsTrialActive(): boolean {
  if (!RAW) return true // default: the tools are public
  if (RAW.toLowerCase() === "off") return false

  const until = Date.parse(RAW)
  // An unparseable value must not silently lock everyone out, which is the
  // failure mode the hardcoded date already produced once. Fail open and let
  // the explicit "off" be the only way to close the gate by accident-proof
  // configuration.
  if (Number.isNaN(until)) return true

  return Date.now() < until
}
