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

// ── Files in the public papers bucket ───────────────────────────────────────
//
// Pages never hand the browser a raw bucket URL any more: a viewer link carries
// the object KEY, and a download goes through /api/pdf, which rate limits and
// answers with a short-lived signed link. That keeps the storage address out of
// the HTML, so "save every link on this page" tools and scrapers walking the
// catalogue get throttled instead of handed the whole archive.

/** Keys are plain relative paths to a PDF — nothing that could climb out. */
export function isSafePdfKey(key: string | null | undefined): key is string {
  if (!key || key.length > 512) return false
  if (key.startsWith("/") || key.includes("\\") || /[\u0000-\u001f]/.test(key)) return false
  if (key.split("/").some(seg => seg === "" || seg === "." || seg === "..")) return false
  return /\.pdf$/i.test(key)
}

/** The object key of a PDF in the public papers bucket, or null for anything else. */
export function r2KeyFromUrl(raw: string | null | undefined): string | null {
  if (!raw) return null
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (url.protocol !== "https:" || url.hostname !== R2_PUBLIC_HOST) return null
  let key: string
  try {
    key = decodeURIComponent(url.pathname.replace(/^\/+/, ""))
  } catch {
    return null
  }
  return isSafePdfKey(key) ? key : null
}

export function encodePdfKey(key: string): string {
  return key.split("/").map(encodeURIComponent).join("/")
}

export function publicUrlForPdfKey(key: string): string {
  return `https://${R2_PUBLIC_HOST}/${encodePdfKey(key)}`
}

/**
 * A same-site link for a PDF: bucket files go through the /api/pdf gate, other
 * hosts we allow (legacy Supabase storage) pass through, anything else is null.
 */
export function gatedPdfHref(
  raw: string | null | undefined,
  opts: { download?: boolean } = {}
): string | null {
  const key = r2KeyFromUrl(raw)
  if (key) return `/api/pdf/${encodePdfKey(key)}${opts.download ? "?dl=1" : ""}`
  return isAllowedPdfUrl(raw) ? raw : null
}

/** `gatedPdfHref` as an absolute URL, for structured data and external tools. */
export function absoluteGatedPdfUrl(raw: string | null | undefined, origin: string): string | null {
  const href = gatedPdfHref(raw)
  if (!href) return null
  return href.startsWith("/") ? `${origin}${href}` : href
}

/**
 * Reads a viewer `qp`/`ms` parameter: a bucket key (current links) or a full
 * URL (links cached before keys were used). Returns a full URL or null.
 */
export function resolveViewerPdfParam(raw: string | null | undefined): string | null {
  if (isSafePdfKey(raw)) return publicUrlForPdfKey(raw)
  return isAllowedPdfUrl(raw) ? raw : null
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
  // Bucket files travel as their key; the viewer signs them per request.
  if (isAllowedPdfUrl(input.qpUrl)) params.set("qp", r2KeyFromUrl(input.qpUrl) ?? input.qpUrl)
  if (isAllowedPdfUrl(input.msUrl)) params.set("ms", r2KeyFromUrl(input.msUrl) ?? input.msUrl)
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
