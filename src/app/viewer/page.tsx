import type { Metadata } from "next"
import ViewerClient from "./ViewerClient"
import { isAllowedPdfUrl, type ViewerDoc } from "@/lib/viewer-link"

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

export default async function ViewerPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams
  const qpRaw = first(sp.qp)
  const msRaw = first(sp.ms)
  const qpUrl = isAllowedPdfUrl(qpRaw) ? qpRaw : null
  const msUrl = isAllowedPdfUrl(msRaw) ? msRaw : null
  const title = first(sp.title) ?? "Past Paper"
  const backPath = safeBackPath(first(sp.back))
  const requestedDoc: ViewerDoc = first(sp.doc) === "ms" ? "ms" : "qp"

  return (
    <ViewerClient
      qpUrl={qpUrl}
      msUrl={msUrl}
      title={title}
      backPath={backPath}
      requestedDoc={requestedDoc}
    />
  )
}
