import { NextRequest, NextResponse } from "next/server"
import { allowPdfAccess, isScraperRequest, signedPdfUrl } from "@/lib/pdfGate"
import { isSafePdfKey } from "@/lib/viewer-link"

/**
 * GET /api/pdf/<key> — download one PDF from the papers bucket.
 *
 * The only way pages link to a bucket file directly. It refuses download tools,
 * rate limits by IP, then redirects to a short-lived signed link — so a person
 * gets their paper in one click, and bulk copying runs into the limit within
 * minutes instead of finishing the archive.
 *
 * `?dl=1` asks the browser to save the file rather than open it.
 */
export const dynamic = "force-dynamic"

const PREFIX = "/api/pdf/"

function keyFromPath(pathname: string): string | null {
  if (!pathname.startsWith(PREFIX)) return null
  try {
    // Decoded here, segment by segment, rather than trusting the framework's
    // params, so a key is decoded exactly once whatever the Next.js version.
    return pathname.slice(PREFIX.length).split("/").map(decodeURIComponent).join("/")
  } catch {
    return null
  }
}

const NO_STORE = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" }

export async function GET(req: NextRequest) {
  const key = keyFromPath(req.nextUrl.pathname)
  if (!isSafePdfKey(key)) {
    return NextResponse.json({ error: "Not found." }, { status: 404, headers: NO_STORE })
  }

  if (await isScraperRequest()) {
    return NextResponse.json(
      { error: "Automated downloads are not allowed. Open the paper on grademax.me." },
      { status: 403, headers: NO_STORE }
    )
  }

  if (!(await allowPdfAccess("file"))) {
    return NextResponse.json(
      { error: "You have downloaded a lot of papers in a short time. Please wait a few minutes and try again." },
      { status: 429, headers: { ...NO_STORE, "Retry-After": "600" } }
    )
  }

  const download = req.nextUrl.searchParams.get("dl") === "1"
  const fileName = key.split("/").pop() ?? "paper.pdf"
  const target = await signedPdfUrl(key, {
    ttlSeconds: 300,
    downloadName: download ? fileName : undefined,
  })

  return NextResponse.redirect(target, { status: 302, headers: NO_STORE })
}
