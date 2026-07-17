// Temporary one-month free-access trial for the worksheet generator
// (/generate) and test builder (/test-builder). Started 2026-07-14.
//
// While the trial is active, the login gates in src/proxy.ts,
// src/app/generate/page.tsx and src/app/test-builder/page.tsx are bypassed.
// The trial ends automatically at TRIAL_ENDS_AT — no code change needed.
//
// To end the trial early: set TRIAL_ENDS_AT to a past date (or make
// isPublicToolsTrialActive return false) and redeploy.
// To remove the trial entirely: delete this file and the three call sites.
const TRIAL_ENDS_AT = Date.parse("2026-08-14T00:00:00Z")

export function isPublicToolsTrialActive(): boolean {
  return Date.now() < TRIAL_ENDS_AT
}
