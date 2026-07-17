import { Metadata } from 'next'
import Link from 'next/link'
import { getSubjectSlugsWithPapers } from '@/lib/papersIndex'
import { cambridgeSeoSubjects, byPopularity } from '@/lib/cambridge-seo'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'
import PastPaperCatalog from '@/components/PastPaperCatalog'
import CambridgeSubjectCards from '@/components/CambridgeSubjectCards'

// Static hub — links are built from the DB index at build time (no ISR writes).
export const revalidate = false

// Build-time year so the title never advertises a stale year.
const CURRENT_YEAR = new Date().getFullYear()

export const metadata: Metadata = {
  title: `Cambridge (CAIE) Past Papers ${CURRENT_YEAR} – Free IGCSE & A Level Mark Schemes`,
  description: `Free Cambridge past papers for IGCSE and AS & A Level with mark schemes (2015–2025). Chemistry 0620, Physics 0625, Maths 0580, Physics 9702 & more — every series, free PDF.`,
  keywords: [
    'Cambridge past papers', 'CAIE past papers', 'CIE past papers',
    `Cambridge past papers ${CURRENT_YEAR}`, `Cambridge past papers ${CURRENT_YEAR - 1}`,
    'Cambridge IGCSE past papers', 'Cambridge A Level past papers',
    'Cambridge AS Level past papers', 'Cambridge International past papers',
    'Cambridge past papers with mark schemes', 'CAIE mark schemes',
    'Cambridge question papers', 'Cambridge past papers free download',
    '0620 past papers', '0625 past papers', '0580 past papers',
    '9702 past papers', '9701 past papers', '9709 past papers',
  ],
  openGraph: {
    title: `Cambridge (CAIE) Past Papers ${CURRENT_YEAR} – Free IGCSE & A Level Mark Schemes`,
    description: `Free Cambridge (CAIE) past papers for every IGCSE and AS & A Level subject with mark schemes. Updated ${CURRENT_YEAR}.`,
    url: 'https://www.grademax.me/cambridge-past-papers',
    siteName: 'GradeMax',
    type: 'website',
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'GradeMax – Free Cambridge Past Papers' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: `Cambridge Past Papers ${CURRENT_YEAR} – Free with Mark Schemes`,
    description: 'Free Cambridge (CAIE) IGCSE & AS/A Level past papers with mark schemes, organised by year and series.',
    images: ['/opengraph-image'],
  },
  alternates: {
    canonical: 'https://www.grademax.me/cambridge-past-papers',
  },
}

const faqs = [
  {
    question: 'Where can I find free Cambridge (CAIE) past papers?',
    answer: 'GradeMax hosts free Cambridge past papers for IGCSE and AS & A Level subjects — including Mathematics 0580, Chemistry 0620, Physics 0625, Biology 0610, Physics 9702 and Chemistry 9701 — with mark schemes, organised by year and exam series from 2015 to 2025.',
  },
  {
    question: 'Are Cambridge past papers available with mark schemes?',
    answer: 'Yes. Every Cambridge question paper on GradeMax is paired with its official mark scheme where published, so you can mark your own attempts the way an examiner would.',
  },
  {
    question: 'What do Cambridge paper codes like 0620/22 mean?',
    answer: 'The four digits are the syllabus code (0620 = IGCSE Chemistry). After the slash, the first digit is the paper number and the second is the time-zone variant — 0620/22 is Paper 2, Variant 2. Variants have equivalent difficulty; they exist because Cambridge examines across time zones.',
  },
  {
    question: 'Which exam series does Cambridge run each year?',
    answer: 'Cambridge examines in up to three series each year: February/March (India zone), May/June, and October/November. GradeMax organises papers by year and series so you can find, say, the May/June 2023 set in two clicks.',
  },
  {
    question: 'What is the difference between CAIE, CIE and Cambridge International?',
    answer: 'They are the same board. Cambridge Assessment International Education (CAIE) was formerly Cambridge International Examinations (CIE) — students still search with both abbreviations.',
  },
  {
    question: `Are ${CURRENT_YEAR - 1} and ${CURRENT_YEAR} Cambridge papers available?`,
    answer: `GradeMax adds each Cambridge series once papers are released publicly. Recent sessions through 2025 are available for most subjects, and new series are added as Cambridge publishes them.`,
  },
]

export default async function CambridgePastPapersLanding() {
  const baseUrl = 'https://www.grademax.me'

  // Only advertise subjects that actually have papers (memoized index, no DB).
  const slugsWithPapers = await getSubjectSlugsWithPapers()
  const available = cambridgeSeoSubjects.filter((s) => slugsWithPapers.has(s.slug))
  const igcse = available.filter((s) => s.level === 'cambridge-igcse').sort(byPopularity)
  const aLevel = available.filter((s) => s.level === 'cambridge-a-level').sort(byPopularity)

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Cambridge Past Papers', url: `${baseUrl}/cambridge-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/cambridge-past-papers`,
        `Cambridge (CAIE) Past Papers ${CURRENT_YEAR} – Free IGCSE & A Level Mark Schemes`,
        'Free Cambridge past papers for IGCSE and AS & A Level with mark schemes, organised by year and exam series.'
      ),
      generateFAQSchema(faqs),
    ],
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-8 md:pt-16 pb-12">
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Free Cambridge Past Papers with Mark Schemes
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Cambridge International (CAIE) past papers for IGCSE and AS &amp; A Level, 2015–2025.
          Every question paper comes with its official mark scheme, organised by year and exam series.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Mathematics 0580, Chemistry 0620, Physics 0625, Biology 0610, Computer Science 0478,
          Physics 9702, Chemistry 9701, Maths 9709 and every other hosted syllabus — completely free.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/past-papers/cambridge" className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors">
            Browse by Subject
          </Link>
          <Link href="#igcse" className="inline-block bg-gray-800 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors border border-gray-700">
            Popular Subjects ↓
          </Link>
        </div>
      </section>

      {/* IGCSE Section */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="igcse">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            Cambridge IGCSE Past Papers
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Free Cambridge IGCSE question papers and mark schemes for every hosted syllabus
          </p>
          <CambridgeSubjectCards subjects={igcse.slice(0, 9)} accent="blue" />
          <div className="text-center mt-6">
            <Link href="/cambridge-igcse-past-papers" className="text-blue-400 hover:text-blue-300 text-sm">
              View all {igcse.length} Cambridge IGCSE subjects →
            </Link>
          </div>
        </div>
      </section>

      {/* A Level Section */}
      <section className="px-4 md:px-8 py-12" id="a-level">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            Cambridge AS &amp; A Level Past Papers
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Free Cambridge International AS and A Level past papers with mark schemes
          </p>
          <CambridgeSubjectCards subjects={aLevel.slice(0, 6)} accent="purple" />
          <div className="text-center mt-6">
            <Link href="/cambridge-a-level-past-papers" className="text-purple-400 hover:text-purple-300 text-sm">
              View all {aLevel.length} Cambridge AS &amp; A Level subjects →
            </Link>
          </div>
        </div>
      </section>

      {/* Understanding codes — unique content that serves code/variant queries */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            How Cambridge Paper Codes Work
          </h2>
          <div className="space-y-6 text-gray-400">
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="font-semibold text-white mb-2">Syllabus codes: 0620, 0580, 9702…</h3>
              <p className="text-sm">Every Cambridge subject has a four-digit syllabus code. IGCSE codes start with 0 (Chemistry is 0620, Mathematics is 0580); AS &amp; A Level codes start with 9 (Physics is 9702, Maths is 9709). Students often search by code alone — each code above links to its full paper archive.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="font-semibold text-white mb-2">Components and variants: 0620/22 = Paper 2, Variant 2</h3>
              <p className="text-sm">The digits after the slash combine the paper number with the time-zone variant. Variant 1, 2 and 3 papers cover the same content at the same difficulty — Cambridge sets different variants for different exam time zones. If your school sat variant 2, practising variants 1 and 3 gives you two extra full papers per session.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="font-semibold text-white mb-2">Exam series: Feb/March, May/June, Oct/Nov</h3>
              <p className="text-sm">Cambridge examines up to three times a year. Papers are labelled by series — m (Feb/March), s (May/June) and w (Oct/Nov) in Cambridge shorthand, so &quot;0620 s23&quot; means the May/June 2023 Chemistry session. GradeMax organises every subject by year and series.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Full catalog: every Cambridge subject with papers, by year + syllabus-code table */}
      <section className="px-4 md:px-8 py-12" id="all-subjects">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">All Cambridge Past Papers by Subject</h2>
          <p className="text-gray-400 mb-8 text-sm">
            Every Cambridge IGCSE and AS &amp; A Level subject with papers on GradeMax, linked by
            year and by syllabus code.
          </p>
          <PastPaperCatalog board="cambridge" levelLabel="" />
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Frequently Asked Questions About Cambridge Past Papers
          </h2>
          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <details key={idx} className="bg-gray-900 rounded-lg border border-gray-800 group">
                <summary className="px-6 py-4 cursor-pointer font-semibold text-gray-200 hover:text-white transition-colors list-none flex justify-between items-center">
                  {faq.question}
                  <svg className="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform flex-shrink-0 ml-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p className="px-6 pb-4 text-gray-400 text-sm leading-relaxed">{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Internal Links */}
      <section className="px-4 md:px-8 py-12 border-t border-gray-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-lg font-semibold mb-6 text-gray-300">Related Resources</h2>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/cambridge-igcse-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Cambridge IGCSE Past Papers</Link>
            <Link href="/cambridge-a-level-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Cambridge A Level Past Papers</Link>
            <Link href="/past-papers/cambridge" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Browse by Subject &amp; Year</Link>
            <Link href="/edexcel-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Edexcel Past Papers</Link>
            <Link href="/subjects" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">All Subjects</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
