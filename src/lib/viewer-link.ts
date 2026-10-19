// Builds links into the on-site PDF viewer (/viewer) and validates which PDF
// hosts it may embed. Only PDFs we host (R2 public bucket, legacy Supabase
// storage) are allowed — /viewer must never become an open frame for
// arbitrary third-party URLs.

export const R2_PUBLIC_HOST = "pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev"

export function isAllowedPdfUrl(raw: string | null | undefined): raw is string {
  if (!raw) return false
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return false
  }
  if (url.protocol !== "https:") return false
  return url.hostname === R2_PUBLIC_HOST || url.hostname.endsWith(".supabase.co")
}

export type ViewerDoc = "qp" | "ms"

/**
 * "single" shows one document at a time; "split" shows the question paper and
 * its mark scheme side by side. Split needs both PDFs, so callers that only
 * have one still get a working single view.
 */
export type ViewerView = "single" | "split"

export function parseViewerView(raw: string | null | undefined): ViewerView {
  return raw === "split" ? "split" : "single"
}

export interface ViewerLinkInput {
  /** Which document the viewer should open first. */
  doc: ViewerDoc
  qpUrl: string | null
  msUrl: string | null
  /** Human-readable paper name shown in the viewer header. */
  title: string
  /** Same-site path the viewer's back link returns to. */
  backPath: string
  /** Open straight into the side-by-side layout. Defaults to "single". */
  view?: ViewerView
}

export function buildViewerHref(input: ViewerLinkInput): string {
  const params = new URLSearchParams()
  if (isAllowedPdfUrl(input.qpUrl)) params.set("qp", input.qpUrl)
  if (isAllowedPdfUrl(input.msUrl)) params.set("ms", input.msUrl)
  params.set("doc", input.doc)
  params.set("title", input.title)
  params.set("back", input.backPath)
  // Only emitted for split so existing single-view links keep their exact URL
  // (and stay a cache hit against anything keyed on the query string).
  if (input.view === "split") params.set("view", "split")
  return `/viewer?${params.toString()}`
}

/** True when a paper has both documents, i.e. side-by-side is meaningful. */
export function canSplit(qpUrl: string | null, msUrl: string | null): boolean {
  return isAllowedPdfUrl(qpUrl) && isAllowedPdfUrl(msUrl)
}
