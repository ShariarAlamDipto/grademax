"use client"

// Unlinked route — not yet in the nav. Visit /visualizer directly.
// Lazy-loads the WebGL app client-side only (no SSR on Cloudflare).

import dynamic from "next/dynamic"

const VisualizerApp = dynamic(() => import("@/components/visualizer/VisualizerApp"), {
  ssr: false,
  loading: () => (
    <div style={{ height: "100vh", display: "grid", placeItems: "center", background: "#0b1220", color: "#94a3b8" }}>
      Loading visualizer…
    </div>
  ),
})

export default function VisualizerPage() {
  return <VisualizerApp />
}
