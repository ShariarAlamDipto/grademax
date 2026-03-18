import { Metadata } from 'next'
import Link from 'next/link'
import { seoSubjects } from '@/lib/seo-subjects'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'Edexcel Worksheet Generator – Free Custom Past Paper Worksheets',
  description: 'Generate free custom worksheets from real Edexcel past paper questions. Choose topics, difficulty, and year range. IGCSE and A Level Physics, Maths, Chemistry, Biology worksheets with mark schemes.',
  keywords: [
    'worksheet generator', 'custom worksheet generator', 'Edexcel worksheet generator',
    'custom worksheets', 'Edexcel worksheets', 'past paper worksheets',
    'create worksheets from past papers', 'exam worksheet generator',
    'IGCSE worksheets', 'A Level worksheets', 'practice worksheets',
    'maths worksheet generator', 'physics worksheet generator',
    'chemistry worksheet generator', 'biology worksheet generator',
    'topic wise worksheets', 'chapterwise worksheets',
    'Edexcel practice worksheets', 'free worksheet generator',
    'IGCSE maths worksheets', 'IGCSE physics worksheets',
    'A Level maths worksheets', 'custom exam papers',
    'create practice papers', 'generate past paper questions',
    'worksheet generator with answers', 'worksheets with mark schemes',
    'Edexcel question paper generator', 'exam paper generator',
    'revision worksheets', 'practice paper generator',
  ],
  openGraph: {
    title: 'Edexcel Worksheet Generator – Free Custom Past Paper Worksheets',
    description: 'Generate free custom worksheets from real Edexcel past papers. IGCSE and A Level with mark schemes.',
    url: 'https://grademax.me/edexcel-worksheets',
    siteName: 'GradeMax',
    type: 'website',
  },
  alternates: {
    canonical: 'https://grademax.me/edexcel-worksheets',
  },
}

const faqs = [
  {
    question: "How does the Edexcel worksheet generator work?",
    answer: "The GradeMax worksheet generator lets you create custom worksheets from real Edexcel past paper questions. Choose your subject, select specific topics, set difficulty levels, pick a year range, and generate a PDF worksheet with its matching mark scheme — all in seconds."
  },
  {
    question: "Is the worksheet generator free?",
    answer: "Yes, the GradeMax worksheet generator is completely free. Generate unlimited custom worksheets for any Edexcel IGCSE or A Level subject with mark schemes included at no cost."
  },
  {
    question: "Can I generate worksheets for specific topics?",
    answer: "Yes! You can select specific topics (chapters) from any subject. For example, generate a worksheet with only Electricity questions from IGCSE Physics, or only Differentiation questions from A Level Pure Maths 1."
  },
  {
    question: "Do generated worksheets include mark schemes?",
    answer: "Yes, every generated worksheet comes with its official Edexcel mark scheme. You can download both the question paper and the mark scheme as separate PDFs."
  },
  {
    question: "What subjects can I generate worksheets for?",
    answer: "You can generate worksheets for any subject available on GradeMax: IGCSE Physics, Maths A, Maths B, Chemistry, Biology, ICT, and A Level Pure Maths 1, Mechanics 1, Statistics 1."
  },
  {
    question: "Can teachers use the worksheet generator?",
    answer: "Absolutely! Teachers use GradeMax to create targeted practice papers for their students. Select specific topics, years, and difficulty levels to create worksheets tailored to your lesson plans."
  },
]

export default function WorksheetsPage() {
  const baseUrl = 'https://grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Edexcel Worksheets', url: `${baseUrl}/edexcel-worksheets` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/edexcel-worksheets`,
        'Edexcel Worksheet Generator – Free Custom Past Paper Worksheets',
        'Generate free custom worksheets from real Edexcel past paper questions.'
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
          Free Edexcel Worksheet Generator
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Create custom worksheets from real Edexcel past paper questions. 
          Choose topics, filter by year and difficulty, and download PDF worksheets with mark schemes — completely free.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Generate IGCSE and A Level practice papers for Physics, Mathematics, Chemistry, Biology, ICT, and more.
        </p>
        <Link 
          href="/generate"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-4 rounded-lg transition-colors text-lg"
        >
          Start Generating Worksheets →
        </Link>
      </section>

      {/* How It Works */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-8">
            How the Worksheet Generator Works
          </h2>
          <div className="grid md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-14 h-14 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">1</div>
              <h3 className="font-semibold mb-2">Choose Subject</h3>
              <p className="text-sm text-gray-400">
                Select any Edexcel IGCSE or A Level subject.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">2</div>
              <h3 className="font-semibold mb-2">Pick Topics</h3>
              <p className="text-sm text-gray-400">
                Select specific chapters or topics to focus on.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">3</div>
              <h3 className="font-semibold mb-2">Set Filters</h3>
              <p className="text-sm text-gray-400">
                Choose year range and difficulty level.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-amber-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">4</div>
              <h3 className="font-semibold mb-2">Download PDF</h3>
              <p className="text-sm text-gray-400">
                Get your worksheet + mark scheme as PDFs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Available Subjects */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2">
            Generate Worksheets for Any Edexcel Subject
          </h2>
          <p className="text-gray-400 text-center mb-8 text-sm">
            Custom worksheets available for all IGCSE and A Level subjects
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {seoSubjects.map((subj) => (
              <Link 
                key={`${subj.level}-${subj.slug}`}
                href="/generate"
                className="bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-blue-600 transition-colors group"
              >
                <h3 className="font-semibold group-hover:text-blue-400 transition-colors mb-1">
                  {subj.levelDisplay} {subj.name}
                </h3>
                <p className="text-xs text-gray-500 mb-2">{subj.examCode} · {subj.topics.length} topics</p>
                <div className="flex flex-wrap gap-1">
                  {subj.topics.slice(0, 3).map((t) => (
                    <span key={t.slug} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{t.name}</span>
                  ))}
                  {subj.topics.length > 3 && <span className="text-xs text-gray-500">+{subj.topics.length - 3}</span>}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Why Use the GradeMax Worksheet Generator?
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
              <h3 className="font-semibold text-blue-400 mb-2">Real Exam Questions</h3>
              <p className="text-sm text-gray-400">Every question comes from actual Edexcel past papers — practice with the real thing, not mock questions.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
              <h3 className="font-semibold text-purple-400 mb-2">Mark Schemes Included</h3>
              <p className="text-sm text-gray-400">Every worksheet comes with its official Edexcel mark scheme so you can check your answers and understand the marking criteria.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
              <h3 className="font-semibold text-green-400 mb-2">Topic-Focused Practice</h3>
              <p className="text-sm text-gray-400">Target your weak areas by generating worksheets for specific topics. Perfect for targeted revision before exams.</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
              <h3 className="font-semibold text-amber-400 mb-2">Completely Free</h3>
              <p className="text-sm text-gray-400">Generate unlimited worksheets with no sign-up required. No hidden fees, no premium plans — free forever.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 md:px-8 py-16 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Start Creating Custom Edexcel Worksheets Now
        </h2>
        <p className="text-gray-400 mb-8 max-w-xl mx-auto">
          Choose your subject, pick topics, and generate a PDF worksheet with mark scheme in under a minute.
        </p>
        <Link 
          href="/generate"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-4 rounded-lg transition-colors text-lg"
        >
          Generate Worksheet →
        </Link>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            Worksheet Generator FAQ
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
            <Link href="/edexcel-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">Edexcel Past Papers</Link>
            <Link href="/edexcel-igcse-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">IGCSE Past Papers</Link>
            <Link href="/edexcel-a-level-past-papers" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">A Level Past Papers</Link>
            <Link href="/subjects" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors">All Subjects</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
