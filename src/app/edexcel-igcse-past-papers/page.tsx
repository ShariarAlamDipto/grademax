import { Metadata } from 'next'
import Link from 'next/link'
import { getSubjectsByLevel } from '@/lib/seo-subjects'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'Edexcel IGCSE Past Papers 2024 – Free with Mark Schemes | All Subjects',
  description: 'Free Edexcel IGCSE past papers with mark schemes for Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), ICT (4IT1). Topic-wise questions from 2014-2024.',
  keywords: [
    'IGCSE past papers', 'IGCSE past papers Edexcel', 'Edexcel IGCSE past papers',
    'IGCSE past papers 2024', 'IGCSE past papers 2023', 'IGCSE past papers free',
    'IGCSE past papers with mark scheme', 'IGCSE past papers free download',
    'international GCSE past papers', 'Pearson Edexcel IGCSE',
    'IGCSE Physics past papers', 'IGCSE Maths past papers',
    'IGCSE Chemistry past papers', 'IGCSE Biology past papers',
    'IGCSE ICT past papers', 'IGCSE topic wise past papers',
    'IGCSE revision papers', 'IGCSE practice papers',
    '4PH1 past papers', '4MA1 past papers', '4MB1 past papers',
    '4CH1 past papers', '4BI1 past papers', '4IT1 past papers',
    'IGCSE question papers', 'IGCSE exam papers Edexcel',
    'IGCSE worksheets', 'IGCSE chapterwise questions',
  ],
  openGraph: {
    title: 'Edexcel IGCSE Past Papers 2024 – Free with Mark Schemes',
    description: 'Free IGCSE past papers for all Edexcel subjects with mark schemes. Organized by topic and year.',
    url: 'https://grademax.me/edexcel-igcse-past-papers',
    siteName: 'GradeMax',
    type: 'website',
  },
  alternates: {
    canonical: 'https://grademax.me/edexcel-igcse-past-papers',
  },
}

const faqs = [
  {
    question: "What IGCSE subjects have past papers available?",
    answer: "GradeMax offers free Edexcel IGCSE past papers for: Physics (4PH1), Mathematics A (4MA1), Mathematics B (4MB1), Chemistry (4CH1), Biology (4BI1), and ICT (4IT1). All papers include mark schemes and are organized by topic."
  },
  {
    question: "How far back do the IGCSE past papers go?",
    answer: "Most IGCSE subjects have past papers from 2014 onwards, with some subjects starting from 2015, 2017, or 2018 depending on when the specification was introduced. All available papers up to 2024 are included."
  },
  {
    question: "Can I practice IGCSE past papers by topic?",
    answer: "Yes! Every IGCSE subject on GradeMax has questions organized by topic/chapter. For example, IGCSE Physics has topics like Forces, Electricity, Waves, and Energy. You can practice all past paper questions on a specific topic."
  },
  {
    question: "What is the difference between IGCSE Maths A and Maths B?",
    answer: "IGCSE Maths A (4MA1) is the standard mathematics qualification suitable for most students. IGCSE Maths B (4MB1) is designed for higher-achieving students and includes more challenging content. Both are offered by Pearson Edexcel."
  },
  {
    question: "Are IGCSE past papers the same as GCSE past papers?",
    answer: "No. IGCSE (International GCSE) papers are set by Pearson Edexcel for international students. They differ from UK GCSE papers in content and structure. GradeMax focuses specifically on Edexcel IGCSE (International) papers."
  },
]

export default function IGCSEPastPapersPage() {
  const subjects = getSubjectsByLevel('igcse')
  const baseUrl = 'https://grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Edexcel Past Papers', url: `${baseUrl}/edexcel-past-papers` },
        { name: 'IGCSE Past Papers', url: `${baseUrl}/edexcel-igcse-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/edexcel-igcse-past-papers`,
        'Edexcel IGCSE Past Papers 2024 – Free with Mark Schemes',
        'Free Edexcel IGCSE past papers for Physics, Maths, Chemistry, Biology and ICT with mark schemes.'
      ),
      generateFAQSchema(faqs),
    ]
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-8 md:pt-16 pb-12">
        <nav className="text-sm text-gray-500 mb-4">
          <Link href="/" className="hover:text-gray-300">Home</Link>
          <span className="mx-2">›</span>
          <Link href="/edexcel-past-papers" className="hover:text-gray-300">Edexcel Past Papers</Link>
          <span className="mx-2">›</span>
          <span className="text-gray-400">IGCSE</span>
        </nav>
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Edexcel IGCSE Past Papers – Free with Mark Schemes
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Access free Pearson Edexcel International GCSE past papers for all subjects. 
          Topic-wise questions with mark schemes from 2014–2024.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Physics (4PH1) · Maths A (4MA1) · Maths B (4MB1) · Chemistry (4CH1) · Biology (4BI1) · ICT (4IT1)
        </p>
      </section>

      {/* Subjects Grid */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Choose Your IGCSE Subject
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {subjects.map((subj) => (
              <Link 
                key={subj.slug}
                href={`/subjects/igcse/${subj.slug}`}
                className="bg-gray-900 rounded-xl p-6 border border-gray-800 hover:border-blue-600 transition-colors group"
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-xl font-semibold group-hover:text-blue-400 transition-colors">
                    IGCSE {subj.name}
                  </h3>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{subj.examCode}</span>
                </div>
                <p className="text-sm text-gray-400 mb-3">{subj.longDescription}</p>
                <div className="flex flex-wrap gap-2 mb-3">
                  {subj.topics.slice(0, 4).map((topic) => (
                    <span key={topic.slug} className="text-xs bg-gray-800 text-gray-400 px-2 py-1 rounded">
                      {topic.name}
                    </span>
                  ))}
                  {subj.topics.length > 4 && (
                    <span className="text-xs text-gray-500">+{subj.topics.length - 4} more</span>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  {subj.yearsAvailable.length} years of papers · {subj.topics.length} topics · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Year Quick Access */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-6">
            IGCSE Past Papers by Year
          </h2>
          <p className="text-gray-400 text-center mb-8 text-sm">
            Jump to Edexcel IGCSE past papers from a specific year
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014].map(year => (
              <Link 
                key={year}
                href={`/browse?level=igcse&year=${year}`}
                className="bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-blue-600 px-4 py-2 rounded-lg text-sm transition-colors"
              >
                {year}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            IGCSE Past Papers FAQ
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
            <Link href="/edexcel-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">All Edexcel Past Papers</Link>
            <Link href="/edexcel-a-level-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">A Level Past Papers</Link>
            <Link href="/edexcel-worksheets" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Custom Worksheets</Link>
            <Link href="/generate" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Worksheet Generator</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
