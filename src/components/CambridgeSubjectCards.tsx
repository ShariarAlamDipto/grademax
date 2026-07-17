import Link from "next/link"
import type { Subject } from "@/lib/subjects"

interface CambridgeSubjectCardsProps {
  subjects: Subject[]
  /** Tailwind hover accent, e.g. "blue" | "purple" — mirrors the Edexcel hubs. */
  accent?: "blue" | "purple"
}

/**
 * Subject card grid for the /cambridge-* landing pages. Each card carries the
 * syllabus code students search by ("Chemistry 0620") and links to the
 * subject's /past-papers hub. Callers pre-filter to subjects that actually
 * have papers, so no card can point at an empty hub.
 */
export default function CambridgeSubjectCards({ subjects, accent = "blue" }: CambridgeSubjectCardsProps) {
  const hover =
    accent === "purple"
      ? { border: "hover:border-purple-600", text: "group-hover:text-purple-400" }
      : { border: "hover:border-blue-600", text: "group-hover:text-blue-400" }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      {subjects.map((s) => (
        <Link
          key={s.slug}
          href={`/past-papers/${s.slug}`}
          className={`bg-gray-900 rounded-lg p-5 border border-gray-800 ${hover.border} transition-colors group`}
        >
          <div className="flex justify-between items-start gap-3 mb-2">
            <h3 className={`font-semibold text-lg ${hover.text} transition-colors`}>
              {s.name}
            </h3>
            {s.examCode && (
              <span className="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded font-mono shrink-0">{s.examCode}</span>
            )}
          </div>
          <p className="text-sm text-gray-400 mb-2">
            {s.name} ({s.examCode}) question papers and mark schemes by year and series.
          </p>
          <p className="text-xs text-gray-500">
            All variants · Mark schemes included · Free PDF
          </p>
        </Link>
      ))}
    </div>
  )
}
