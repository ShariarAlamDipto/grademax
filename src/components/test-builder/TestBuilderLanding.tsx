import Link from 'next/link'
import { generateOrganizationSchema, generateBreadcrumbSchema, generateWebPageSchema, generateFAQSchema } from '@/lib/seo-schema'

// Public, indexable landing rendered at /test-builder for logged-out visitors
// (signed-in users get the actual tool). This is the page that ranks for
// "test builder" / "custom test paper" queries — the tool itself needs auth,
// so without this Google only ever saw a 307 to /login.

const SUBJECTS = [
  { name: 'IGCSE Physics',                 code: '4PH1', href: '/subjects/igcse/physics' },
  { name: 'IGCSE Mathematics B',           code: '4MB1', href: '/subjects/igcse/maths-b' },
  { name: 'IGCSE Chemistry',               code: '4CH1', href: '/subjects/igcse/chemistry' },
  { name: 'IGCSE Biology',                 code: '4BI1', href: '/subjects/igcse/biology' },
  { name: 'IGCSE Human Biology',           code: '4HB1', href: '/past-papers/human-biology' },
  { name: 'IGCSE Further Pure Mathematics', code: '4PM1', href: '/past-papers/further-pure-maths' },
]

const faqs = [
  {
    question: 'What is the GradeMax Test Builder?',
    answer: 'The Test Builder lets you create your own custom Edexcel test papers. Instead of downloading a fixed past paper, you hand-pick individual questions from real Edexcel IGCSE past papers — filtered by topic, difficulty, and year — and download a print-ready PDF test with its matching mark scheme.',
  },
  {
    question: 'Is the Test Builder free?',
    answer: 'Yes. You need a free GradeMax account to build and download tests, but there is no charge — sign in and start building.',
  },
  {
    question: 'Which subjects does the Test Builder support?',
    answer: 'Edexcel IGCSE Physics (4PH1), Mathematics B (4MB1), Chemistry (4CH1), Biology (4BI1), Human Biology (4HB1), and Further Pure Mathematics (4PM1). More subjects are added as their question banks are classified by topic.',
  },
  {
    question: 'How is the Test Builder different from the Worksheet Generator?',
    answer: 'The Worksheet Generator automatically assembles a worksheet from your chosen topics in one click. The Test Builder gives you full control: you preview and select each individual question yourself, so you can build a mock exam that matches exactly what you want to practise.',
  },
  {
    question: 'Do built tests come with mark schemes?',
    answer: 'Yes. Every test you build comes with the matching official Edexcel mark scheme pages for the questions you selected, downloadable as a separate PDF.',
  },
  {
    question: 'Can teachers use the Test Builder for their classes?',
    answer: 'Absolutely. Teachers use it to compose targeted class tests and homework from real past paper questions — pick the exact questions that match your lesson plan and print the PDF for your students.',
  },
]

export default function TestBuilderLanding() {
  const baseUrl = 'https://www.grademax.me'

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Test Builder', url: `${baseUrl}/test-builder` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/test-builder`,
        'Edexcel Test Builder – Create Custom Test Papers Free',
        'Build custom Edexcel IGCSE test papers question by question from real past papers, with mark schemes.'
      ),
      {
        '@type': 'WebApplication',
        name: 'GradeMax Test Builder',
        url: `${baseUrl}/test-builder`,
        applicationCategory: 'EducationalApplication',
        operatingSystem: 'Web',
        offers: { '@type': 'Offer', price: '0', priceCurrency: 'GBP' },
        description: 'Create custom Edexcel IGCSE test papers by selecting individual questions from real past papers, filtered by topic, difficulty, and year.',
      },
      generateFAQSchema(faqs),
    ],
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-8 md:pt-16 pb-12">
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Edexcel Test Builder
        </h1>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-4">
          Create your own custom test papers from real Edexcel IGCSE past paper questions.
          Hand-pick every question by topic, difficulty, and year — then download a print-ready
          PDF with its mark scheme.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Free with a GradeMax account. Physics, Mathematics, Chemistry, Biology and more.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/login?next=/test-builder"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-4 rounded-lg transition-colors text-lg"
          >
            Start Building — Free →
          </Link>
          <Link
            href="/edexcel-worksheets"
            className="inline-block border border-gray-700 hover:border-gray-500 text-gray-200 font-semibold px-8 py-4 rounded-lg transition-colors text-lg"
          >
            Or generate a worksheet
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-8">
            How the Test Builder Works
          </h2>
          <div className="grid md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-14 h-14 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">1</div>
              <h3 className="font-semibold mb-2">Choose Subject</h3>
              <p className="text-sm text-gray-400">
                Pick an Edexcel IGCSE subject with a classified question bank.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">2</div>
              <h3 className="font-semibold mb-2">Filter Questions</h3>
              <p className="text-sm text-gray-400">
                Narrow by topic, difficulty, and exam year.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">3</div>
              <h3 className="font-semibold mb-2">Pick Each Question</h3>
              <p className="text-sm text-gray-400">
                Preview real past paper questions and add the ones you want.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-amber-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">4</div>
              <h3 className="font-semibold mb-2">Download Your Test</h3>
              <p className="text-sm text-gray-400">
                Get a print-ready PDF test plus its mark scheme.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Subjects */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-3">
            Subjects You Can Build Tests For
          </h2>
          <p className="text-center text-gray-400 mb-8 max-w-2xl mx-auto">
            Every question is segmented from real Pearson Edexcel IGCSE past papers and
            classified by topic, so your custom test mirrors the real exam.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {SUBJECTS.map((s) => (
              <Link
                key={s.code}
                href={s.href}
                className="border border-gray-800 hover:border-gray-600 rounded-lg p-4 transition-colors"
              >
                <p className="font-semibold">{s.name}</p>
                <p className="text-sm text-gray-500 mt-1">{s.code}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ (visible content backing the ItemList schema — no fabricated FAQPage markup) */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-8">
            Test Builder FAQs
          </h2>
          <div className="space-y-6">
            {faqs.map((faq) => (
              <div key={faq.question}>
                <h3 className="font-semibold text-lg mb-2">{faq.question}</h3>
                <p className="text-gray-400 leading-relaxed">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Cross-links */}
      <section className="px-4 md:px-8 py-12 text-center">
        <h2 className="text-xl font-bold mb-4">More Free Edexcel Resources</h2>
        <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
          <Link href="/edexcel-past-papers" className="border border-gray-800 hover:border-gray-600 rounded-full px-4 py-2 transition-colors">Edexcel Past Papers</Link>
          <Link href="/edexcel-igcse-past-papers" className="border border-gray-800 hover:border-gray-600 rounded-full px-4 py-2 transition-colors">IGCSE Past Papers</Link>
          <Link href="/edexcel-a-level-past-papers" className="border border-gray-800 hover:border-gray-600 rounded-full px-4 py-2 transition-colors">A Level Past Papers</Link>
          <Link href="/edexcel-worksheets" className="border border-gray-800 hover:border-gray-600 rounded-full px-4 py-2 transition-colors">Worksheet Generator</Link>
          <Link href="/subjects" className="border border-gray-800 hover:border-gray-600 rounded-full px-4 py-2 transition-colors">All Subjects</Link>
        </div>
      </section>
    </main>
  )
}
