import Link from "next/link"
import "./tools-banner.css"

/**
 * A banner for the past-paper hub pages that sends visitors to the two
 * practice tools: the Worksheet Generator (students) and the Test Builder
 * (teachers). Both tools ask for a sign-in, so the line under the buttons says
 * what signing in gives.
 *
 * A plain server component: no session lookup, so it adds no database work to
 * the hub pages.
 */

export type ToolsBannerBoard = "edexcel" | "cambridge"

interface ToolsBannerProps {
  board: ToolsBannerBoard
}

const COPY: Record<ToolsBannerBoard, { lead: string; scope: string }> = {
  edexcel: {
    lead: "Past papers show you what you got wrong. Pick the chapters you find hard and the Worksheet Generator builds a practice sheet from real questions, with its mark scheme.",
    scope: "Works for every Edexcel IGCSE and International A Level subject in the tools.",
  },
  cambridge: {
    lead: "Past papers show you what you got wrong. Pick the chapters you find hard and the Worksheet Generator builds a practice sheet from real questions, with its mark scheme.",
    scope: "Cambridge IGCSE Physics (0625) is in the tools now, along with every Edexcel subject.",
  },
}

export default function ToolsBanner({ board }: ToolsBannerProps) {
  const copy = COPY[board]
  return (
    <aside className="tb-wrap" aria-labelledby={`tools-banner-${board}`}>
      <div className="tb">
        <div className="tb-text">
          <p className="tb-eyebrow">Practise your weak points</p>
          <h2 id={`tools-banner-${board}`} className="tb-title">
            Stop re-reading. Practise the topics you keep losing marks on.
          </h2>
          <p className="tb-lead">{copy.lead}</p>
          <p className="tb-note">
            <b>Teachers:</b> choose questions from real papers and download a print-ready test with the Test Builder.
          </p>
        </div>
        <div className="tb-actions">
          <Link href="/generate" className="btn-beacon">Generate a worksheet</Link>
          <Link href="/test-builder" className="btn-ghost-amber">Test Builder for teachers</Link>
          <p className="tb-fine">Sign in to save your worksheets and track your progress. {copy.scope}</p>
        </div>
      </div>
    </aside>
  )
}
