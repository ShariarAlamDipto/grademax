import Link from "next/link"
import type { Subject } from "@/lib/subjects"
import { getPapersIndex } from "@/lib/papersIndex"
import {
  cambridgeSeoSubjects,
  cambridgeLevelShort,
  cambridgeLevelSeo,
  cambridgeFaqs,
} from "@/lib/cambridge-seo"
import {
  generateOrganizationSchema,
  generateBreadcrumbSchema,
  generateWebPageSchema,
  generateFAQSchema,
} from "@/lib/seo-schema"

const BASE_URL = "https://www.grademax.me"

function serializeJsonLd(schema: object): string {
  return JSON.stringify(schema).replace(/</g, "\\u003c")
}

interface CambridgeQpLandingProps {
  subject: Subject
  slug: string
}

/**
 * /qp/{syllabus-code} landing for a Cambridge subject (e.g. /qp/0620). The
 * Edexcel /qp pages are SEOSubject-shaped (topics, worksheet CTAs) — Cambridge
 * subjects have no topic classification, so this renders the code-query page
 * from the Subject entry + the memoized papers index alone (no DB round-trips).
 */
export default async function CambridgeQpLanding({ subject, slug }: CambridgeQpLandingProps) {
  const code = subject.examCode ?? ""
  const lvl = cambridgeLevelShort(subject) // "IGCSE" | "A Level" (breadcrumbs/H1)
  const lvlSeo = cambridgeLevelSeo(subject) // "IGCSE" | "AS & A Level" (copy)
  const faqs = cambridgeFaqs(subject)

  // Years with published papers, newest first — from the shared memoized index.
  const { yearsBySubject } = await getPapersIndex()
  const years = Array.from(yearsBySubject.get(subject.slug) ?? []).sort((a, b) => b - a)
  const yearRange = years.length > 0 ? `${years[years.length - 1]}–${years[0]}` : "2015–2025"

  const pageUrl = `${BASE_URL}/qp/${slug}`
  const schema = {
    "@context": "https://schema.org",
    "@graph": [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: "Home", url: BASE_URL },
        { name: "Cambridge Past Papers", url: `${BASE_URL}/cambridge-past-papers` },
        { name: `${subject.name} ${code}`, url: pageUrl },
      ]),
      generateWebPageSchema(
        pageUrl,
        `${subject.name} ${code} Past Papers – Cambridge ${lvlSeo}`,
        `Free Cambridge ${lvlSeo} ${subject.name} (${code}) past papers with mark schemes.`
      ),
      generateFAQSchema(faqs),
      {
        "@type": "CollectionPage",
        name: `Cambridge ${lvl} ${subject.name} (${code}) Past Papers Collection`,
        description: `Complete collection of Cambridge ${lvlSeo} ${subject.name} (${code}) past papers with mark schemes, ${yearRange}.`,
        url: pageUrl,
        isPartOf: { "@id": `${BASE_URL}/#website` },
        about: {
          "@type": "Course",
          name: `Cambridge ${lvl} ${subject.name}`,
          provider: { "@type": "Organization", name: "Cambridge Assessment International Education (CAIE)" },
          courseCode: code,
        },
      },
    ],
  }

  const related = cambridgeSeoSubjects.filter(
    (s) => s.level === subject.level && s.slug !== subject.slug
  )

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(schema) }} />

      {/* Breadcrumb */}
      <nav className="max-w-6xl mx-auto px-4 py-4 text-sm text-gray-400">
        <ol className="flex items-center gap-2 flex-wrap">
          <li><Link href="/" className="hover:text-white">Home</Link></li>
          <li>/</li>
          <li><Link href="/cambridge-past-papers" className="hover:text-white">Cambridge Past Papers</Link></li>
          <li>/</li>
          <li className="text-white">{subject.name} {code}</li>
        </ol>
      </nav>

      {/* Hero */}
      <section className="px-4 md:px-8 pt-4 pb-12 max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <span className="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-sm font-medium">
            Cambridge International (CAIE)
          </span>
          <span className="bg-gray-800 text-gray-300 px-3 py-1 rounded-full text-sm font-mono">
            {code}
          </span>
          <span className="bg-green-900/30 text-green-400 px-3 py-1 rounded-full text-sm">
            Free
          </span>
        </div>

        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Cambridge {lvl} {subject.name} ({code}) Past Papers
        </h1>

        <p className="text-lg text-gray-300 max-w-4xl mb-3">
          Free {subject.name} {code} question papers and mark schemes for Cambridge {lvlSeo},
          {" "}{yearRange}. Every hosted series — February/March, May/June and October/November —
          with all time-zone variants, as free PDFs.
        </p>
        <p className="text-sm text-gray-500 mb-8">
          {years.length > 0 ? `${years.length} years of papers` : "Papers"} · All variants · Mark schemes included · Free download
        </p>

        <div className="flex flex-wrap gap-4">
          <Link
            href={`/past-papers/${subject.slug}`}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Papers by Year
          </Link>
          <Link
            href="/cambridge-past-papers"
            className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors border border-gray-700"
          >
            All Cambridge Subjects
          </Link>
        </div>
      </section>

      {/* Past Papers by Year */}
      {years.length > 0 && (
        <section className="px-4 md:px-8 py-12 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl font-bold mb-6">
              {subject.name} {code} Past Papers by Year
            </h2>
            <div className="flex flex-wrap gap-3">
              {years.map((year) => (
                <Link
                  key={year}
                  href={`/past-papers/${subject.slug}/${year}`}
                  className="bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-lg px-4 py-2 text-sm transition-colors"
                >
                  {subject.name} {year}
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Variant explainer — unique content that answers "{code}/22"-style queries */}
      <section className="px-4 md:px-8 py-12 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold mb-6">How {code} Paper Numbers Work</h2>
        <div className="bg-gray-900 rounded-lg p-6 border border-gray-800 text-gray-400 text-sm leading-relaxed space-y-3">
          <p>
            Cambridge references every exam as <span className="text-white font-mono">{code}/paper-variant</span> —
            so <span className="text-white font-mono">{code}/22</span> is Paper 2, Variant 2 of {subject.name}.
            Variants 1, 2 and 3 are set for different time zones at equivalent difficulty, which means each
            session usually gives you two or three full papers to practise per paper number.
          </p>
          <p>
            Series shorthand: <span className="text-white font-mono">m</span> = February/March,{" "}
            <span className="text-white font-mono">s</span> = May/June,{" "}
            <span className="text-white font-mono">w</span> = October/November — a file named{" "}
            <span className="text-white font-mono">{code.toLowerCase()}_s23_qp_22</span> is the May/June 2023
            Paper 2 Variant 2 question paper.
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            {subject.name} {code} — Frequently Asked Questions
          </h2>
          <div className="space-y-3">
            {faqs.map((faq, idx) => (
              <details key={idx} className="bg-gray-900 rounded-lg border border-gray-800 group">
                <summary className="px-5 py-4 cursor-pointer font-medium text-gray-200 hover:text-white transition-colors list-none flex justify-between items-center">
                  {faq.question}
                  <svg className="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform flex-shrink-0 ml-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p className="px-5 pb-4 text-gray-400 text-sm leading-relaxed">{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Related Subjects */}
      <section className="px-4 md:px-8 py-10 border-t border-gray-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-lg font-semibold mb-6 text-gray-300">Other Cambridge {lvlSeo} Subjects</h2>
          <div className="flex flex-wrap justify-center gap-3">
            {related.map((s) => (
              <Link
                key={s.slug}
                href={`/qp/${(s.examCode ?? "").toLowerCase()}`}
                className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors"
              >
                {s.name} {s.examCode}
              </Link>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs text-gray-500">
            <Link href="/cambridge-past-papers" className="hover:text-white transition-colors">All Cambridge Past Papers</Link>
            <span>·</span>
            <Link href="/cambridge-igcse-past-papers" className="hover:text-white transition-colors">IGCSE Past Papers</Link>
            <span>·</span>
            <Link href="/cambridge-a-level-past-papers" className="hover:text-white transition-colors">AS &amp; A Level Past Papers</Link>
            <span>·</span>
            <Link href="/past-papers/cambridge" className="hover:text-white transition-colors">Browse by Subject</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
