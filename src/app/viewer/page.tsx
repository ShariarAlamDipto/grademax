import { Suspense } from "react"
import type { Metadata } from "next"
import ViewerClient from "./ViewerClient"

// Static shell — the client component reads the query string at runtime, so
// this route costs nothing to serve and never triggers ISR writes.
export const dynamic = "force-static"

// noindex (not robots.txt-disallowed): every viewer URL is a query-string
// variant of a canonical /past-papers page, so Google must be able to crawl
// it to see the noindex. The canonical content stays on the paper pages.
export const metadata: Metadata = {
  title: "Past Paper Viewer",
  robots: { index: false, follow: true },
}

export default function ViewerPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-black" />}>
      <ViewerClient />
    </Suspense>
  )
}
