import Link from "next/link"
import { buildViewerHref, canSplit } from "@/lib/viewer-link"

interface PaperRowProps {
  /** The paper's own page. Null when the paper_number has no usable slug. */
  href: string | null
  /** "Paper 1R", "Unit 4", "Paper 2 · Variant 2". */
  label: string
  /** Cambridge component reference students search verbatim, e.g. "9702/22". */
  code?: string
  qpUrl: string | null
  msUrl: string | null
  /** Paper name shown in the viewer header. */
  viewerTitle: string
  /** Same-site path the viewer's back link returns to. */
  backPath: string
  /** Data booklet / formula sheet, when the sitting has one. */
  dataUrl?: string | null
  /** Anchor id so deep links can jump to a single paper. */
  id?: string
}

/**
 * One paper in a listing — name on the left, actions on the right.
 *
 * Every action opens the on-site viewer rather than the raw PDF, so "Both"
 * (side by side) is always one click away from wherever a student is browsing.
 * The paper's own page keeps the direct downloads.
 */
export default function PaperRow({
  href,
  label,
  code,
  qpUrl,
  msUrl,
  viewerTitle,
  backPath,
  dataUrl,
  id,
}: PaperRowProps) {
  const viewer = { qpUrl, msUrl, title: viewerTitle, backPath }
  const splitAvailable = canSplit(qpUrl, msUrl)

  return (
    <div className="gm-paper-row" id={id}>
      {href ? (
        <Link href={href} className="gm-paper-name">
          {label}
          {code && <span className="gm-paper-code">{code}</span>}
        </Link>
      ) : (
        <span className="gm-paper-name">
          {label}
          {code && <span className="gm-paper-code">{code}</span>}
        </span>
      )}

      <div className="gm-paper-actions">
        {qpUrl ? (
          <Link
            href={buildViewerHref({ doc: "qp", ...viewer })}
            className="gm-paper-action"
            title={`${viewerTitle} question paper`}
          >
            QP
          </Link>
        ) : (
          <span className="gm-paper-action" data-muted="true" title="Question paper not available">
            QP
          </span>
        )}

        {msUrl ? (
          <Link
            href={buildViewerHref({ doc: "ms", ...viewer })}
            className="gm-paper-action"
            title={`${viewerTitle} mark scheme`}
          >
            MS
          </Link>
        ) : (
          <span className="gm-paper-action" data-muted="true" title="Mark scheme not available">
            MS
          </span>
        )}

        {splitAvailable ? (
          <Link
            href={buildViewerHref({ doc: "qp", view: "split", ...viewer })}
            className="gm-paper-action"
            title="Open the question paper and mark scheme side by side"
          >
            Both
          </Link>
        ) : (
          <span className="gm-paper-action" data-muted="true" title="Needs both documents">
            Both
          </span>
        )}

        {dataUrl && (
          <a
            href={dataUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="gm-paper-action"
            title="Data booklet"
          >
            Data
          </a>
        )}
      </div>
    </div>
  )
}
