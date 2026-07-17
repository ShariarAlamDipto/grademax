import type { Metadata } from "next"

// Metadata-only layout: the page is a client component and cannot export metadata itself.
export const metadata: Metadata = {
  title: "Visualizer",
}

export default function VisualizerLayout({ children }: { children: React.ReactNode }) {
  return children
}
