import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"

export const dynamic = "force-dynamic"

const VALID_SESSIONS = new Set(["Jan", "May-Jun", "Oct-Nov", "Specimen"])
const VALID_TYPES = new Set(["QP", "MS"])
const YEAR_RE = /^\d{4}$/

// GET /api/admin/scraper — check if scraper is available in this environment
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  return NextResponse.json({
    available: process.env.NODE_ENV === "development",
    env: process.env.NODE_ENV,
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
  // Subject must be alphanumeric + spaces + underscores only
  if (!/^[\w\s-]+$/.test(subject)) {
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
    execFile("python", args, { cwd: scraperRoot, timeout: 120000 }, (error, stdout, stderr) => {
      if (error) {
        resolve(NextResponse.json({
          success: false,
          error: error.message,
          stderr: stderr?.slice(0, 2000),
          stdout: stdout?.slice(0, 2000),
        }, { status: 500 }))
        return
      }
      resolve(NextResponse.json({
        success: true,
        stdout: stdout?.slice(0, 5000),
        stderr: stderr?.slice(0, 1000),
      }))
    })
  })
}
