import { Metadata } from 'next'
import Link from 'next/link'
import { getSubjectSlugsWithPapers } from '@/lib/papersIndex'
import { cambridgeSeoSubjects, byPopularity } from '@/lib/cambridge-seo'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'
import PastPaperCatalog from '@/components/PastPaperCatalog'
import CambridgeSubjectCards from '@/components/CambridgeSubjectCards'

// Static hub — links are built from the DB index at build time (no ISR writes).
export const revalidate = false

const CURRENT_YEAR = new Date().getFullYear()

export const metadata: Metadata = {
  title: `Cambridge A Level Past Papers ${CURRENT_YEAR} – AS & A Level Mark Schemes (CAIE)`,
  description: `Free Cambridge International AS & A Level past papers with mark schemes, 2015–2025. Physics 9702, Chemistry 9701, Biology 9700, Maths 9709, Economics 9708 & more — free PDF.`,
  keywords: [
    'Cambridge A Level past papers', 'Cambridge AS Level past papers',
    'CAIE A Level past papers', 'CIE A Level past papers',
    `Cambridge A Level past papers ${CURRENT_YEAR}`, `Cambridge A Level past papers ${CURRENT_YEAR - 1}`,
    'Cambridge International A Level past papers', 'AS and A Level past papers',
    'Cambridge A Level mark schemes', 'A Level past papers free download',
    '9702 past papers', '9701 past papers', '9700 past papers',
    '9709 past papers', '9708 past papers', '9706 past papers',
    'Cambridge A Level Physics past papers', 'Cambridge A Level Chemistry past papers',
    'Cambridge A Level Maths past papers', 'Cambridge A Level Biology past papers',
  ],
  openGraph: {
    title: `Cambridge A Level Past Papers ${CURRENT_YEAR} – AS & A Level Mark Schemes (CAIE)`,
    description: 'Free Cambridge International AS & A Level past papers for every hosted syllabus with mark schemes, organised by year and exam series.',
    url: 'https://www.grademax.me/cambridge-a-level-past-papers',
    siteName: 'GradeMax',
    type: 'website',
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'GradeMax – Free Cambridge A Level Past Papers' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: `Cambridge A Level Past Papers ${CURRENT_YEAR} – Free with Mark Schemes`,
    description: 'Free Cambridge AS & A Level past papers with mark schemes for every hosted subject.',
    images: ['/opengraph-image'],
  },
  alternates: {
    canonical: 'https://www.grademax.me/cambridge-a-level-past-papers',
  },
}

const faqs = [
  {
    question: 'Which Cambridge A Level subjects have past papers on GradeMax?',
    answer: 'All hosted Cambridge International AS & A Level syllabuses — including Physics 9702, Chemistry 9701, Biology 9700, Mathematics 9709, Further Maths 9231, Economics 9708, Accounting 9706, Business 9609 and Computer Science 9608 — with question papers and mark schemes.',
  },
  {
    question: 'Do the papers cover both AS and A Level?',
    answer: 'Yes. Cambridge examines AS components (typically Papers 1–3) and A Level components (typically Papers 4–5) under the same syllabus code, and both appear on each subject’s page organised by year and series.',
  },
  {
    question: 'How do I read an A Level paper reference like 9702/22?',
    answer: 'The four-digit syllabus code (9702 = Physics) is followed by the component: paper number then time-zone variant. So 9702/22 is Physics Paper 2, Variant 2 — variants are set for different time zones at equivalent difficulty.',
  },
  {
    question: 'What years of Cambridge A Level past papers are available?',
    answer: 'Papers cover 2015 through 2025 for most syllabuses, across the February/March, May/June and October/November series where the subject was examined.',
  },
]

export default async function CambridgeALevelPastPapersLanding() {
  const baseUrl = 'https://www.grademax.me'

  const slugsWithPapers = await getSubjectSlugsWithPapers()
  const aLevel = cambridgeSeoSubjects
    .filter((s) => s.level === 'cambridge-a-level' && slugsWithPapers.has(s.slug))
    .sort(byPopularity)

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Cambridge Past Papers', url: `${baseUrl}/cambridge-past-papers` },
        { name: 'Cambridge A Level Past Papers', url: `${baseUrl}/cambridge-a-level-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/cambridge-a-level-past-papers`,
        `Cambridge A Level Past Papers ${CURRENT_YEAR} – AS & A Level with Mark Schemes`,
        'Free Cambridge International AS & A Level past papers with mark schemes for every hosted syllabus, organised by year and exam series.'
      ),
      generateFAQSchema(faqs),
    ],
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      {/* Breadcrumb */}
      <nav className="max-w-6xl mx-auto px-4 py-4 text-sm text-gray-400">
        <ol className="flex items-center gap-2 flex-wrap">
          <li><Link href="/" className="hover:text-white">Home</Link></li>
          <li>/</li>
          <li><Link href="/cambridge-past-papers" className="hover:text-white">Cambridge Past Papers</Link></li>
          <li>/</li>
          <li className="text-white">AS &amp; A Level</li>
        </ol>
      </nav>

      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-4 md:pt-10 pb-12">
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Cambridge AS &amp; A Level Past Papers
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Free Cambridge International (CAIE) AS &amp; A Level question papers and mark schemes for {aLevel.length} subjects,
          2015–2025 — organised by year, series and variant.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Every syllabus is listed with its code — Physics 9702, Chemistry 9701, Biology 9700,
          Mathematics 9709, Economics 9708 and more — so you can jump straight to the papers you searched for.
        </p>
      </section>

      {/* All A Level subjects */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="subjects">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            All Cambridge AS &amp; A Level Subjects
          </h2>
          <p className="text-gray-400 text-center mb-8">
            {aLevel.length} syllabuses with past papers and mark schemes
          </p>
          <CambridgeSubjectCards subjects={aLevel} accent="purple" />
        </div>
      </section>

      {/* By-year catalog + syllabus-code table */}
      <section className="px-4 md:px-8 py-12" id="by-year">
        <div className="max-w-6xl mx-auto">
          <PastPaperCatalog board="cambridge" level="cambridge-a-level" levelLabel="AS & A Level" />
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Cambridge AS &amp; A Level Past Papers — FAQs
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
            <Link href="/cambridge-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">All Cambridge Past Papers</Link>
            <Link href="/cambridge-igcse-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Cambridge IGCSE Past Papers</Link>
            <Link href="/past-papers/cambridge" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Browse by Subject &amp; Year</Link>
            <Link href="/edexcel-a-level-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Edexcel A Level Past Papers</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
