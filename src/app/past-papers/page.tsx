
import { createClient } from "@supabase/supabase-js"
import Link from "next/link"
import { pastPaperSubjects, type Subject } from "@/lib/subjects"

export const revalidate = 3600

function SubjectCard({ subject }: { subject: Subject }) {
  return (
    <Link href={`/past-papers/${subject.slug}`}>
      <div
        className="group relative bg-gray-50 dark:bg-white/[0.03] border border-gray-200 dark:border-gray-800 rounded-xl p-5
                    transition-colors duration-200 hover:bg-gray-100 dark:hover:bg-white/[0.06] hover:border-gray-400 dark:hover:border-gray-600"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white text-base">
              {subject.name}
            </h3>
            <span className="inline-block mt-1 text-xs text-gray-400 dark:text-gray-600">
              Edexcel {subject.level === "ial" ? "A Level" : "IGCSE"}
            </span>
          </div>
          <span className="text-gray-300 dark:text-gray-700 group-hover:text-gray-600 dark:group-hover:text-gray-400 transition-colors">
            →
          </span>
        </div>
      </div>
    </Link>
  )
}

export default async function PastPapersPage() {
  // Fetch subject names that actually have papers in the database
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )

  const { data: paperRows } = await supabase
    .from("papers")
    .select("subjects!inner(name)")
    .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")

  const subjectsWithPapers = new Set<string>(
    (paperRows ?? []).map((r: { subjects: { name: string } | { name: string }[] }) => {
      const s = Array.isArray(r.subjects) ? r.subjects[0] : r.subjects
      return s?.name ?? ""
    }).filter(Boolean)
  )

  // Only show subjects that exist in our static list AND have data in DB
  const availableSubjects = pastPaperSubjects.filter(s => subjectsWithPapers.has(s.name))

  const igcse = availableSubjects.filter((s) => s.level === "igcse")
  const ial = availableSubjects.filter((s) => s.level === "ial")

  return (
    <main className="min-h-screen bg-white dark:bg-black text-gray-900 dark:text-white px-6 py-12">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-3">Past Papers</h1>
          <p className="text-gray-500 dark:text-white/50 max-w-lg mx-auto">
            Free Edexcel IGCSE and A Level past papers with mark schemes.
            Download question papers organized by year and session.
          </p>
        </div>

        {/* IGCSE */}
        {igcse.length > 0 && (
          <section className="mb-12">
            <div className="flex items-center gap-3 mb-6">
              <h2 className="text-2xl font-bold">IGCSE</h2>
              <span className="text-xs text-gray-500 dark:text-white/30 font-medium bg-gray-100 dark:bg-white/5 px-2.5 py-1 rounded-full">
                {igcse.length} subjects
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {igcse.map((s) => (
                <SubjectCard key={s.slug} subject={s} />
              ))}
            </div>
          </section>
        )}

        {/* IAL */}
        {ial.length > 0 && (
          <section>
            <div className="flex items-center gap-3 mb-6">
              <h2 className="text-2xl font-bold">A Level (IAL)</h2>
              <span className="text-xs text-gray-500 dark:text-white/30 font-medium bg-gray-100 dark:bg-white/5 px-2.5 py-1 rounded-full">
                {ial.length} subjects
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {ial.map((s) => (
                <SubjectCard key={s.slug} subject={s} />
              ))}
            </div>
          </section>
        )}

        {availableSubjects.length === 0 && (
          <div className="text-center py-20 text-gray-400 dark:text-white/40">
            <p className="text-lg font-medium mb-2">No papers available yet</p>
            <p className="text-sm">Papers are being uploaded. Check back soon.</p>
          </div>
        )}
      </div>
    </main>
  )
}
