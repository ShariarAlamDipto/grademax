import { Metadata } from 'next'
import Link from 'next/link'
import { getSubjectsByLevel } from '@/lib/seo-subjects'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'Edexcel A Level Past Papers 2024 – Free IAL with Mark Schemes',
  description: 'Free Edexcel A Level (IAL) past papers with mark schemes. Pure Maths 1 (WMA11), Mechanics 1 (WME01), Statistics 1 (WST01). Topic-wise questions from 2014-2024.',
  keywords: [
    'A Level past papers', 'A Level past papers Edexcel', 'Edexcel A Level past papers',
    'A Level past papers 2024', 'A Level past papers 2023', 'A Level past papers free',
    'IAL past papers', 'International A Level past papers', 'Edexcel IAL past papers',
    'A Level Maths past papers', 'A Level Maths past papers Edexcel',
    'A Level Maths past papers by topic', 'A Level Maths topic wise',
    'Pure Maths 1 past papers', 'P1 past papers', 'WMA11 past papers',
    'Mechanics 1 past papers', 'M1 past papers', 'WME01 past papers',
    'Statistics 1 past papers', 'S1 past papers', 'WST01 past papers',
    'A Level past papers with mark scheme', 'A Level revision papers',
    'A Level question papers Edexcel', 'A Level exam papers',
    'A Level differentiation past papers', 'A Level integration past papers',
    'A Level algebra past papers', 'A Level probability past papers',
    'A Level topic wise questions', 'A Level chapterwise past papers',
    'A Level worksheets', 'A Level practice papers',
  ],
  openGraph: {
    title: 'Edexcel A Level Past Papers 2024 – Free IAL with Mark Schemes',
    description: 'Free A Level past papers for all Edexcel IAL units with mark schemes. Organized by topic and year.',
    url: 'https://grademax.me/edexcel-a-level-past-papers',
    siteName: 'GradeMax',
    type: 'website',
  },
  alternates: {
    canonical: 'https://grademax.me/edexcel-a-level-past-papers',
  },
}

const faqs = [
  {
    question: "What A Level units have past papers available?",
    answer: "GradeMax offers free Edexcel IAL past papers for: Pure Mathematics 1 (WMA11/P1), Mechanics 1 (WME01/M1), and Statistics 1 (WST01/S1). More units including P2, P3, M2, S2, and Further Pure are being added."
  },
  {
    question: "What is the difference between IAL and A Level?",
    answer: "IAL (International A Level) is Pearson Edexcel's international version of A Levels, taken by students worldwide. The content is similar to UK A Levels but exams are available in January and June sessions. GradeMax focuses on Edexcel IAL papers."
  },
  {
    question: "Can I practice A Level Maths past papers by topic?",
    answer: "Yes! Each A Level unit on GradeMax has questions organized by topic. For example, Pure Maths 1 topics include Algebra, Coordinate Geometry, Sequences & Series, Differentiation, and Integration."
  },
  {
    question: "Are A Level mark schemes included?",
    answer: "Yes, every A Level past paper on GradeMax comes with its official Pearson Edexcel mark scheme. You can view the mark scheme alongside the question paper or generate worksheets with mark schemes included."
  },
  {
    question: "How do I revise for Edexcel A Level Maths?",
    answer: "1) Practice topic-wise past paper questions to master individual concepts. 2) Generate custom worksheets to mix questions from different years. 3) Do full timed papers under exam conditions. 4) Always check the mark scheme to understand the marking criteria."
  },
]

export default function ALevelPastPapersPage() {
  const subjects = getSubjectsByLevel('ial')
  const baseUrl = 'https://grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Edexcel Past Papers', url: `${baseUrl}/edexcel-past-papers` },
        { name: 'A Level Past Papers', url: `${baseUrl}/edexcel-a-level-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/edexcel-a-level-past-papers`,
        'Edexcel A Level Past Papers 2024 – Free IAL with Mark Schemes',
        'Free Edexcel IAL past papers for Pure Maths, Mechanics, Statistics with mark schemes.'
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
          <span className="text-gray-400">A Level</span>
        </nav>
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Edexcel A Level (IAL) Past Papers – Free with Mark Schemes
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Access free Pearson Edexcel International A Level past papers. 
          Topic-wise questions with mark schemes from 2014–2024.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Pure Mathematics 1 (WMA11) · Mechanics 1 (WME01) · Statistics 1 (WST01) · More coming soon
        </p>
      </section>

      {/* Units Grid */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            A Level Units Available
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {subjects.map((subj) => (
              <Link 
                key={subj.slug}
                href={`/subjects/ial/${subj.slug}`}
                className="bg-gray-900 rounded-xl p-6 border border-gray-800 hover:border-purple-600 transition-colors group"
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-xl font-semibold group-hover:text-purple-400 transition-colors">
                    {subj.name}
                  </h3>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{subj.examCode}</span>
                </div>
                <p className="text-sm text-gray-400 mb-3">{subj.longDescription}</p>
                <div className="flex flex-wrap gap-2 mb-3">
                  {subj.topics.map((topic) => (
                    <span key={topic.slug} className="text-xs bg-gray-800 text-gray-400 px-2 py-1 rounded">
                      {topic.name}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-gray-500">
                  {subj.yearsAvailable.length} years · {subj.topics.length} topics · Mark schemes included
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
            A Level Past Papers by Year
          </h2>
          <div className="flex flex-wrap justify-center gap-3">
            {[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014].map(year => (
              <Link 
                key={year}
                href={`/browse?level=ial&year=${year}`}
                className="bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-purple-600 px-4 py-2 rounded-lg text-sm transition-colors"
              >
                {year}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Topic-Wise Section */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2">
            Practice A Level Past Papers by Topic
          </h2>
          <p className="text-gray-400 text-center mb-8 text-sm">
            Focus your revision on specific topics with chapter-wise past paper questions
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {subjects.map((subj) => (
              <div key={subj.slug} className="bg-gray-900 rounded-lg p-5 border border-gray-800">
                <h3 className="font-semibold text-purple-400 mb-3">{subj.name}</h3>
                <ul className="space-y-2">
                  {subj.topics.map((topic) => (
                    <li key={topic.slug}>
                      <Link 
                        href={`/subjects/ial/${subj.slug}/${topic.slug}`}
                        className="text-sm text-gray-400 hover:text-white transition-colors"
                      >
                        {topic.name} →
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            A Level Past Papers FAQ
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
      <section className="px-4 md:px-8 py-12 bg-gray-950 border-t border-gray-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-lg font-semibold mb-6 text-gray-300">Related Resources</h2>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/edexcel-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">All Edexcel Past Papers</Link>
            <Link href="/edexcel-igcse-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">IGCSE Past Papers</Link>
            <Link href="/edexcel-worksheets" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Custom Worksheets</Link>
            <Link href="/generate" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Worksheet Generator</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
