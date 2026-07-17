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
  title: `Cambridge IGCSE Past Papers ${CURRENT_YEAR} – All Subjects with Mark Schemes (CAIE)`,
  description: `Free Cambridge IGCSE past papers with mark schemes, 2015–2025. Maths 0580, Chemistry 0620, Physics 0625, Biology 0610, Computer Science 0478 and every hosted syllabus — free PDF.`,
  keywords: [
    'Cambridge IGCSE past papers', 'CAIE IGCSE past papers', 'CIE IGCSE past papers',
    `Cambridge IGCSE past papers ${CURRENT_YEAR}`, `Cambridge IGCSE past papers ${CURRENT_YEAR - 1}`,
    'IGCSE past papers Cambridge', 'Cambridge IGCSE mark schemes',
    'Cambridge IGCSE question papers', 'IGCSE past papers free download',
    '0580 past papers', '0620 past papers', '0625 past papers',
    '0610 past papers', '0478 past papers', '0500 past papers',
    'Cambridge IGCSE Maths past papers', 'Cambridge IGCSE Chemistry past papers',
    'Cambridge IGCSE Physics past papers', 'Cambridge IGCSE Biology past papers',
  ],
  openGraph: {
    title: `Cambridge IGCSE Past Papers ${CURRENT_YEAR} – All Subjects with Mark Schemes (CAIE)`,
    description: 'Free Cambridge IGCSE past papers for every hosted syllabus with mark schemes, organised by year and exam series.',
    url: 'https://www.grademax.me/cambridge-igcse-past-papers',
    siteName: 'GradeMax',
    type: 'website',
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: 'GradeMax – Free Cambridge IGCSE Past Papers' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: `Cambridge IGCSE Past Papers ${CURRENT_YEAR} – Free with Mark Schemes`,
    description: 'Free Cambridge IGCSE past papers with mark schemes for every hosted subject.',
    images: ['/opengraph-image'],
  },
  alternates: {
    canonical: 'https://www.grademax.me/cambridge-igcse-past-papers',
  },
}

const faqs = [
  {
    question: 'Which Cambridge IGCSE subjects have past papers on GradeMax?',
    answer: 'All hosted Cambridge IGCSE syllabuses — including Mathematics 0580, Additional Maths 0606, Chemistry 0620, Physics 0625, Biology 0610, Computer Science 0478, English First Language 0500, Economics 0455 and Accounting 0452 — with question papers and mark schemes by year and series.',
  },
  {
    question: 'What years of Cambridge IGCSE past papers are available?',
    answer: 'Papers cover 2015 through 2025 for most syllabuses, across the February/March, May/June and October/November series where the subject was examined.',
  },
  {
    question: 'How do I read an IGCSE paper reference like 0620/22?',
    answer: 'The four-digit syllabus code (0620 = Chemistry) is followed by the component: paper number then time-zone variant. So 0620/22 is Chemistry Paper 2, Variant 2. All variants of a paper have equivalent difficulty.',
  },
  {
    question: 'Are Cambridge IGCSE mark schemes free too?',
    answer: 'Yes — every question paper is paired with its official mark scheme where published, viewable online or downloadable as a free PDF.',
  },
]

export default async function CambridgeIgcsePastPapersLanding() {
  const baseUrl = 'https://www.grademax.me'

  const slugsWithPapers = await getSubjectSlugsWithPapers()
  const igcse = cambridgeSeoSubjects
    .filter((s) => s.level === 'cambridge-igcse' && slugsWithPapers.has(s.slug))
    .sort(byPopularity)

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Cambridge Past Papers', url: `${baseUrl}/cambridge-past-papers` },
        { name: 'Cambridge IGCSE Past Papers', url: `${baseUrl}/cambridge-igcse-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/cambridge-igcse-past-papers`,
        `Cambridge IGCSE Past Papers ${CURRENT_YEAR} – All Subjects with Mark Schemes`,
        'Free Cambridge IGCSE past papers with mark schemes for every hosted syllabus, organised by year and exam series.'
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
          <li className="text-white">IGCSE</li>
        </ol>
      </nav>

      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-4 md:pt-10 pb-12">
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Cambridge IGCSE Past Papers
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Free Cambridge (CAIE) IGCSE question papers and mark schemes for {igcse.length} subjects,
          2015–2025 — organised by year, series and variant.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Every syllabus is listed with its code — Mathematics 0580, Chemistry 0620, Physics 0625,
          Biology 0610 and more — so you can jump straight to the papers you searched for.
        </p>
      </section>

      {/* All IGCSE subjects */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="subjects">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            All Cambridge IGCSE Subjects
          </h2>
          <p className="text-gray-400 text-center mb-8">
            {igcse.length} syllabuses with past papers and mark schemes
          </p>
          <CambridgeSubjectCards subjects={igcse} accent="blue" />
        </div>
      </section>

      {/* By-year catalog + syllabus-code table */}
      <section className="px-4 md:px-8 py-12" id="by-year">
        <div className="max-w-6xl mx-auto">
          <PastPaperCatalog board="cambridge" level="cambridge-igcse" levelLabel="IGCSE" />
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Cambridge IGCSE Past Papers — FAQs
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
            <Link href="/cambridge-a-level-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Cambridge A Level Past Papers</Link>
            <Link href="/past-papers/cambridge" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Browse by Subject &amp; Year</Link>
            <Link href="/edexcel-igcse-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Edexcel IGCSE Past Papers</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
