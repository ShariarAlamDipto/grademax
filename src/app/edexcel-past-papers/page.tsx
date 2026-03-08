import { Metadata } from 'next'
import Link from 'next/link'
import { seoSubjects, getSubjectsByLevel } from '@/lib/seo-subjects'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'Edexcel Past Papers 2024 – Free IGCSE & A Level with Mark Schemes',
  description: 'Download free Edexcel past papers for IGCSE and A Level with mark schemes. Physics, Maths, Chemistry, Biology, ICT, Statistics & more. Topic-wise questions from 2010-2024.',
  keywords: [
    'Edexcel past papers', 'Edexcel past papers free', 'Edexcel past papers 2024',
    'Edexcel past papers 2023', 'Edexcel past papers with answers',
    'Pearson Edexcel past papers', 'Edexcel exam papers',
    'Edexcel IGCSE past papers', 'Edexcel A Level past papers',
    'Edexcel past papers with mark scheme', 'Edexcel question papers',
    'Edexcel practice papers', 'Edexcel revision papers',
    'past papers Edexcel free download', 'Edexcel past papers online',
  ],
  openGraph: {
    title: 'Edexcel Past Papers 2024 – Free IGCSE & A Level with Mark Schemes',
    description: 'Free Edexcel past papers for all subjects with mark schemes. IGCSE and A Level.',
    url: 'https://grademax.me/edexcel-past-papers',
    siteName: 'GradeMax',
    type: 'website',
  },
  alternates: {
    canonical: 'https://grademax.me/edexcel-past-papers',
  },
}

const faqs = [
  {
    question: "Where can I find free Edexcel past papers?",
    answer: "GradeMax provides free Edexcel past papers for all IGCSE and A Level subjects including Physics, Maths, Chemistry, Biology, and ICT. All papers from 2014-2024 are available with official mark schemes, organized by topic and year."
  },
  {
    question: "Are Edexcel past papers available with mark schemes?",
    answer: "Yes, every Edexcel past paper on GradeMax comes with its official mark scheme. You can view the mark scheme alongside the question paper or download both as PDFs."
  },
  {
    question: "What Edexcel subjects have past papers available?",
    answer: "GradeMax offers past papers for: IGCSE Physics (4PH1), IGCSE Maths A (4MA1), IGCSE Maths B (4MB1), IGCSE Chemistry (4CH1), IGCSE Biology (4BI1), IGCSE ICT (4IT1), A Level Pure Maths 1 (WMA11), A Level Mechanics 1 (WME01), and A Level Statistics 1 (WST01)."
  },
  {
    question: "Can I practice Edexcel past papers by topic?",
    answer: "Yes! All Edexcel past paper questions on GradeMax are organized by topic (chapter-wise). You can browse a specific topic like Electricity, Algebra, or Differentiation and practice all past paper questions on that topic with mark schemes."
  },
  {
    question: "How do I generate custom worksheets from Edexcel past papers?",
    answer: "Use the free GradeMax Worksheet Generator: select your subject, choose topics, pick year ranges and difficulty levels, then generate a custom PDF worksheet with its matching mark scheme in seconds."
  },
  {
    question: "Are Edexcel 2024 past papers available?",
    answer: "Yes, GradeMax regularly updates its database with the latest Edexcel past papers. 2024 papers are available for most subjects as they are released by Pearson Edexcel."
  },
]

export default function EdexcelPastPapersPage() {
  const igcse = getSubjectsByLevel('igcse')
  const ial = getSubjectsByLevel('ial')
  const baseUrl = 'https://grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Edexcel Past Papers', url: `${baseUrl}/edexcel-past-papers` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/edexcel-past-papers`,
        'Edexcel Past Papers 2024 – Free IGCSE & A Level with Mark Schemes',
        'Download free Edexcel past papers for IGCSE and A Level with mark schemes.'
      ),
      generateFAQSchema(faqs),
    ]
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      
      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-8 md:pt-16 pb-12">
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Free Edexcel Past Papers with Mark Schemes
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Access 14+ years of Pearson Edexcel past papers for IGCSE and A Level. 
          All papers include official mark schemes, organized by topic and year.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Download Edexcel exam papers for Physics, Mathematics, Chemistry, Biology, ICT, 
          Pure Maths, Mechanics, Statistics and more — completely free.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/generate" className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors">
            Generate Custom Worksheet
          </Link>
          <Link href="#igcse" className="inline-block bg-gray-800 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors border border-gray-700">
            Browse Past Papers ↓
          </Link>
        </div>
      </section>

      {/* IGCSE Section */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="igcse">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            Edexcel IGCSE Past Papers
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Free Pearson Edexcel International GCSE past papers with mark schemes for all subjects
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {igcse.map((subj) => (
              <Link 
                key={subj.slug}
                href={`/subjects/igcse/${subj.slug}`}
                className="bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-blue-600 transition-colors group"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg group-hover:text-blue-400 transition-colors">
                    IGCSE {subj.name}
                  </h3>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{subj.examCode}</span>
                </div>
                <p className="text-sm text-gray-400 mb-2">{subj.shortDescription}</p>
                <p className="text-xs text-gray-500">
                  {subj.topics.length} topics · {subj.yearsAvailable[0]}–{subj.yearsAvailable[subj.yearsAvailable.length - 1]} · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
          <div className="text-center mt-6">
            <Link href="/edexcel-igcse-past-papers" className="text-blue-400 hover:text-blue-300 text-sm">
              View all IGCSE subjects and topics →
            </Link>
          </div>
        </div>
      </section>

      {/* A Level Section */}
      <section className="px-4 md:px-8 py-12" id="ial">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            Edexcel A Level (IAL) Past Papers
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Free Pearson Edexcel International A Level past papers with mark schemes
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {ial.map((subj) => (
              <Link 
                key={subj.slug}
                href={`/subjects/ial/${subj.slug}`}
                className="bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-purple-600 transition-colors group"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg group-hover:text-purple-400 transition-colors">
                    A Level {subj.name}
                  </h3>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{subj.examCode}</span>
                </div>
                <p className="text-sm text-gray-400 mb-2">{subj.shortDescription}</p>
                <p className="text-xs text-gray-500">
                  {subj.topics.length} topics · {subj.yearsAvailable[0]}–{subj.yearsAvailable[subj.yearsAvailable.length - 1]} · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
          <div className="text-center mt-6">
            <Link href="/edexcel-a-level-past-papers" className="text-purple-400 hover:text-purple-300 text-sm">
              View all A Level units and topics →
            </Link>
          </div>
        </div>
      </section>

      {/* How to Use */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            How to Use Edexcel Past Papers Effectively
          </h2>
          <div className="space-y-6 text-gray-400">
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="font-semibold text-white mb-2">1. Practice by Topic First</h3>
              <p className="text-sm">Start by practicing topic-wise past paper questions. This builds confidence on individual concepts before attempting full papers. Use GradeMax&apos;s topic browser to focus on weak areas.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="font-semibold text-white mb-2">2. Generate Custom Worksheets</h3>
              <p className="text-sm">Use the free worksheet generator to create targeted practice papers. Mix questions from different years and topics to simulate real exam conditions.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <h3 className="font-semibold text-white mb-2">3. Check Mark Schemes Carefully</h3>
              <p className="text-sm">Always review the official Edexcel mark scheme after attempting questions. Note the marking criteria and required working — this is where most marks are lost.</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Frequently Asked Questions About Edexcel Past Papers
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
            <Link href="/edexcel-igcse-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">IGCSE Past Papers</Link>
            <Link href="/edexcel-a-level-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">A Level Past Papers</Link>
            <Link href="/edexcel-worksheets" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Custom Worksheets</Link>
            <Link href="/generate" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Worksheet Generator</Link>
            <Link href="/subjects" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">All Subjects</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
