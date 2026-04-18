import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

const VALID_SESSIONS = new Set(["Jan", "May-Jun", "Oct-Nov", "Specimen"])
const VALID_TYPES = new Set(["QP", "MS"])
const YEAR_RE = /^\d{4}$/

/**
 * Attempt to log a scraper run. Silently ignores if the table doesn't exist yet.
 * Create table with:
 *   CREATE TABLE IF NOT EXISTS scraper_runs (
 *     id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 *     created_at timestamptz DEFAULT now(),
 *     subject text NOT NULL,
 *     session text,
 *     year text,
 *     paper_type text,
 *     success boolean NOT NULL,
 *     output text,
 *     error_text text
 *   );
 */
async function logRun(params: {
  subject: string; session?: string; year?: string; paperType?: string
  success: boolean; output?: string; errorText?: string
}) {
  try {
    const db = getSupabaseAdmin()
    if (!db) return
    await db.from("scraper_runs").insert({
      subject: params.subject,
      session: params.session || null,
      year: params.year || null,
      paper_type: params.paperType || null,
      success: params.success,
      output: (params.output || "").slice(0, 5000),
      error_text: (params.errorText || "").slice(0, 2000) || null,
    })
  } catch {
    // Table may not exist yet — non-fatal
  }
}

// GET /api/admin/scraper — check if scraper is available + return recent run history
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  let recentRuns: unknown[] = []
  try {
    const { data } = await db
      .from("scraper_runs")
      .select("id, created_at, subject, session, year, paper_type, success, output, error_text")
      .order("created_at", { ascending: false })
      .limit(20)
    recentRuns = data || []
  } catch {
    // Table may not exist yet
  }

  return NextResponse.json({
    available: process.env.NODE_ENV === "development",
    env: process.env.NODE_ENV,
    recentRuns,
  })
}

// POST /api/admin/scraper — trigger the Grademax scraper (development only)
export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  if (process.env.NODE_ENV !== "development") {
    return NextResponse.json(
      { error: "Scraper can only be triggered from a local development environment. Run the scraper script directly on your machine." },
      { status: 503 }
    )
  }

  const body = await req.json().catch(() => ({}))
  const { subject, session, year, paperType } = body as Record<string, string>

  if (!subject || typeof subject !== "string") {
    return NextResponse.json({ error: "subject is required" }, { status: 400 })
  }
  if (session && !VALID_SESSIONS.has(session)) {
    return NextResponse.json({ error: "Invalid session" }, { status: 400 })
  }
  if (year && !YEAR_RE.test(year)) {
    return NextResponse.json({ error: "Invalid year" }, { status: 400 })
  }
  if (paperType && !VALID_TYPES.has(paperType)) {
    return NextResponse.json({ error: "Invalid paperType" }, { status: 400 })
  }
  // Subject must be alphanumeric + single spaces + underscores + hyphens only (no control chars)
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_ -]*$/.test(subject) || /[\t\n\r\v\f]/.test(subject)) {
    return NextResponse.json({ error: "Invalid subject name" }, { status: 400 })
  }

  // Dynamic import so it only loads in Node.js (not during edge builds)
  const { execFile } = await import("child_process")
  const path = await import("path")

  const scraperRoot = path.resolve(process.cwd(), "..", "grademax-scraper")

  // Build args array — passed directly to execFile, never shell-interpolated
  const args = ["scrape_missing_papers.py", "--subject", subject]
  if (session) args.push("--session", session)
  if (year) args.push("--year", year)
  if (paperType) args.push("--type", paperType)

  return new Promise<NextResponse>((resolve) => {
    execFile("python", args, { cwd: scraperRoot, timeout: 120000 }, async (error, stdout, stderr) => {
      if (error) {
        await logRun({ subject, session, year, paperType, success: false, output: stdout, errorText: error.message + "\n" + stderr })
        resolve(NextResponse.json({
          success: false,
          error: error.message,
          stderr: stderr?.slice(0, 2000),
          stdout: stdout?.slice(0, 2000),
        }, { status: 500 }))
        return
      }
      await logRun({ subject, session, year, paperType, success: true, output: stdout })
      resolve(NextResponse.json({
        success: true,
        stdout: stdout?.slice(0, 5000),
        stderr: stderr?.slice(0, 1000),
      }))
    })
  })
}
