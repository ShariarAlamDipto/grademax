import type { Metadata } from "next"
import { after } from "next/server"
import { headers } from "next/headers"
import ViewerClient from "./ViewerClient"
import Link from "next/link"
import { parseViewerView, resolveViewerPdfParam, type ViewerDoc, type ViewerView } from "@/lib/viewer-link"
import { allowPdfAccess, isScraperRequest, signIfBucketPdf } from "@/lib/pdfGate"
import { trackUsage } from "@/lib/trackUsage"

// Dynamic: the whole page is derived from query params, which are only known
// per-request. Reading `searchParams` server-side renders the correct PDF on the
// first paint — no flash, no hydration mismatch. (An earlier `force-static` +
// client `useSearchParams` version SSR'd the "Paper not found" fallback and
// swapped to the PDF on the client, which flashed "Browse Past Papers" and threw
// a hydration error.) This is a lightweight render — no DB work — and the route
// is noindex, so it never touches the ISR write meter.
export const dynamic = "force-dynamic"

// noindex (not robots.txt-disallowed): every viewer URL is a query-string
// variant of a canonical /past-papers page. The canonical content lives on the
// paper pages; this utility view stays out of the index.
export const metadata: Metadata = {
  title: "Past Paper Viewer",
  robots: { index: false, follow: true },
}

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}

function safeBackPath(raw: string | undefined): string {
  // Same-site paths only — reject absolute/protocol-relative URLs.
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) return raw
  return "/past-papers"
}

const BOT_UA = /bot|crawl|spider|slurp|preview|curl|wget|python-requests|headless|lighthouse|facebookexternalhit/i

// Best-effort subject from the back path: /past-papers/<subject>/… or
// /past-papers/cambridge/<subject>/…
function subjectFromBackPath(backPath: string): string | null {
  const segments = backPath.split("?")[0].split("/").filter(Boolean)
  if (segments[0] !== "past-papers") return null
  const slug = segments[1] === "cambridge" ? segments[2] : segments[1]
  if (!slug) return null
  return slug.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")
}

export default async function ViewerPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams
  const qpRaw = first(sp.qp)
  const msRaw = first(sp.ms)
  // A bucket key (current links) or a full URL (links cached before that).
  const qpUrl = resolveViewerPdfParam(qpRaw)
  const msUrl = resolveViewerPdfParam(msRaw)
  const title = first(sp.title) ?? "Past Paper"
  const backPath = safeBackPath(first(sp.back))
  const requestedDoc: ViewerDoc = first(sp.doc) === "ms" ? "ms" : "qp"
  // Split needs both documents; asking for it with only one falls back to single.
  const requestedView: ViewerView =
    qpUrl && msUrl ? parseViewerView(first(sp.view)) : "single"

  // Record which paper was opened. `after()` runs once the response has been
  // sent, so tracking never adds latency to the render; trackUsage itself
  // swallows failures. Bots are skipped — /viewer is noindex but crawlers
  // still follow links into it.
  const userAgent = (await headers()).get("user-agent") ?? ""
  if ((qpUrl || msUrl) && !BOT_UA.test(userAgent)) {
    const pdfPath = (() => {
      try { return new URL(qpUrl ?? msUrl ?? "").pathname } catch { return null }
    })()
    after(() =>
      trackUsage({
        feature: "paper_view",
        subject_name: subjectFromBackPath(backPath),
        metadata: { title, doc: requestedDoc, view: requestedView, path: pdfPath, back: backPath },
      })
    )
  }

  // The gate: download tools get nothing, and each IP has an allowance of
  // papers per ten minutes and per day. Within it, the browser receives
  // short-lived signed links rather than the bucket's public address.
  if (qpUrl || msUrl) {
    if (await isScraperRequest()) {
      return <ViewerBlocked backPath={backPath} message="Automated downloads are not allowed." />
    }
    if (!(await allowPdfAccess("view"))) {
      return (
        <ViewerBlocked
          backPath={backPath}
          message="You have opened a lot of papers in a short time. Please wait a few minutes, then reload this page."
        />
      )
    }
  }
  const [qpSigned, msSigned] = await Promise.all([signIfBucketPdf(qpUrl), signIfBucketPdf(msUrl)])

  return (
    <ViewerClient
      qpUrl={qpSigned}
      msUrl={msSigned}
      title={title}
      backPath={backPath}
      requestedDoc={requestedDoc}
      requestedView={requestedView}
    />
  )
}

function ViewerBlocked({ backPath, message }: { backPath: string; message: string }) {
  return (
    <main style={{ maxWidth: "36rem", margin: "0 auto", padding: "4rem 1.25rem", textAlign: "center" }}>
      <h1 style={{ fontSize: "1.3rem", fontWeight: 700, marginBottom: "0.75rem" }}>Paper unavailable right now</h1>
      <p style={{ fontSize: "0.9rem", color: "var(--gm-text-2)", lineHeight: 1.7, marginBottom: "1.25rem" }}>{message}</p>
      <Link href={backPath} className="gm-link">Back to past papers</Link>
    </main>
  )
}
