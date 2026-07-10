"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { track } from "@vercel/analytics"
import type { ViewerDoc } from "@/lib/viewer-link"

const DOC_LABELS: Record<ViewerDoc, string> = {
  qp: "Question Paper",
  ms: "Mark Scheme",
}

interface ViewerClientProps {
  qpUrl: string | null
  msUrl: string | null
  title: string
  backPath: string
  requestedDoc: ViewerDoc
}

export default function ViewerClient({
  qpUrl,
  msUrl,
  title,
  backPath,
  requestedDoc,
}: ViewerClientProps) {
  // Server and client compute the same initial doc from the same props, so the
  // first paint already shows the right PDF (no hydration mismatch).
  const initialDoc: ViewerDoc =
    requestedDoc === "ms" ? (msUrl ? "ms" : "qp") : qpUrl ? "qp" : "ms"
  const [doc, setDoc] = useState<ViewerDoc>(initialDoc)

  const activeUrl = doc === "ms" ? msUrl : qpUrl

  useEffect(() => {
    if (activeUrl) track("pdf_view", { doc, paper: title })
  }, [doc, activeUrl, title])

  if (!qpUrl && !msUrl) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold mb-3">Paper not found</h1>
          <p className="text-white/50 text-sm mb-6">
            This viewer link is missing or invalid. Browse all past papers to find
            the one you need.
          </p>
          <Link
            href="/past-papers"
            className="inline-flex px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-semibold transition-colors"
          >
            Browse Past Papers
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4">
        {/* Header: back link + title */}
        <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
          <div className="min-w-0">
            <Link
              href={backPath}
              className="text-xs text-white/50 hover:text-white transition-colors"
            >
              ← Back to paper page
            </Link>
            <h1 className="text-base sm:text-lg font-bold truncate">
              {title} – {DOC_LABELS[doc]}
            </h1>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* QP / MS toggle */}
            <div className="inline-flex rounded-lg border border-white/15 overflow-hidden">
              {(["qp", "ms"] as const).map((kind) => {
                const available = kind === "qp" ? Boolean(qpUrl) : Boolean(msUrl)
                const active = doc === kind
                return (
                  <button
                    key={kind}
                    type="button"
                    disabled={!available}
                    onClick={() => setDoc(kind)}
                    className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
                      active
                        ? "bg-white/15 text-white"
                        : available
                          ? "text-white/50 hover:text-white"
                          : "text-white/20 cursor-not-allowed"
                    }`}
                  >
                    {DOC_LABELS[kind]}
                  </button>
                )
              })}
            </div>

            {activeUrl && (
              <a
                href={activeUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => track("pdf_download", { doc, paper: title })}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30 hover:bg-blue-500/25 transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download PDF
              </a>
            )}
          </div>
        </div>

        {/* PDF frame */}
        {activeUrl ? (
          <iframe
            key={activeUrl}
            src={activeUrl}
            title={`${title} – ${DOC_LABELS[doc]}`}
            className="w-full h-[78vh] min-h-[420px] rounded-xl border border-white/10 bg-white"
          />
        ) : (
          <div className="w-full h-[40vh] rounded-xl border border-white/10 flex items-center justify-center text-white/40 text-sm">
            {DOC_LABELS[doc]} is not available for this paper.
          </div>
        )}

        <p className="text-xs text-white/30 mt-3">
          PDF not loading?{" "}
          {activeUrl && (
            <a
              href={activeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-white/60 transition-colors"
            >
              Open it directly
            </a>
          )}
        </p>
      </div>
    </main>
  )
}
