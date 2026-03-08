// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import Link from "next/link"

const igcseSubjects = [
  { name: "Physics", code: "4PH1", slug: "physics", topics: 8, years: "2014–2024" },
  { name: "Mathematics A", code: "4MA1", slug: "maths-a", topics: 7, years: "2015–2024" },
  { name: "Mathematics B", code: "4MB1", slug: "maths-b", topics: 10, years: "2014–2024" },
  { name: "Chemistry", code: "4CH1", slug: "chemistry", topics: 5, years: "2017–2024" },
  { name: "Biology", code: "4BI1", slug: "biology", topics: 5, years: "2017–2024" },
  { name: "ICT", code: "4IT1", slug: "ict", topics: 4, years: "2018–2024" },
]

const ialSubjects = [
  { name: "Pure Mathematics 1", code: "WMA11", slug: "pure-maths-1", topics: 5, years: "2014–2024" },
  { name: "Mechanics 1", code: "WME01", slug: "mechanics-1", topics: 8, years: "2014–2024" },
  { name: "Statistics 1", code: "WST01", slug: "statistics-1", topics: 5, years: "2014–2024" },
]

const faqs = [
  {
    q: "Where can I find free Edexcel IGCSE past papers?",
    a: "GradeMax offers free Edexcel IGCSE past papers for Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), and ICT (4IT1). All papers include mark schemes and are organized by topic and year from 2014–2024."
  },
  {
    q: "How do I generate a custom Edexcel worksheet?",
    a: "Use the GradeMax Worksheet Generator to create custom worksheets from real Edexcel past paper questions. Select your subject, choose specific topics, set difficulty levels, pick year ranges, and generate a PDF worksheet with its matching mark scheme in seconds — completely free."
  },
  {
    q: "What Edexcel A Level past papers are available?",
    a: "GradeMax provides Edexcel IAL past papers for Pure Mathematics 1 (WMA11), Mechanics 1 (WME01), and Statistics 1 (WST01), with more units being added regularly. Papers span from 2014–2024 with full mark schemes included."
  },
  {
    q: "Can I practice Edexcel past papers by topic?",
    a: "Yes! GradeMax organizes all Edexcel past paper questions by topic (chapter-wise). Browse questions for specific topics like Electricity, Algebra, Differentiation, or Organic Chemistry and practice with instant access to mark schemes."
  },
  {
    q: "Is GradeMax free to use?",
    a: "Yes, GradeMax is completely free. Access all Edexcel IGCSE and A Level past papers, generate unlimited custom worksheets, and practice topic-wise questions at no cost."
  },
  {
    q: "How are the past papers organized on GradeMax?",
    a: "Past papers are organized in three ways: by subject (e.g., IGCSE Physics), by topic/chapter (e.g., Electricity, Waves, Forces), and by year (e.g., 2024, 2023). You can also generate custom worksheets combining questions from multiple years and topics."
  },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white">
      {/* Hero Section - Primary Keywords */}
      <section className="text-center px-4 md:px-8 pt-8 md:pt-16">
        <h1 className="text-3xl md:text-5xl font-bold text-white mb-4">
          Free Edexcel Past Papers, Topic-Wise Questions &amp; Custom Worksheets
        </h1>
        <p className="hero-description text-lg md:text-xl text-gray-300 max-w-3xl mx-auto mb-4">
          Access 14+ years of Edexcel IGCSE and A Level past papers with mark schemes. 
          Generate custom worksheets from real exam questions and practice topic-wise — all completely free.
        </p>
        <p className="text-sm text-gray-500 max-w-2xl mx-auto mb-8">
          Pearson Edexcel past papers for Physics, Mathematics, Chemistry, Biology, ICT &amp; more. 
          Organized by topic, chapter, and year with instant mark scheme access.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-4">
          <Link 
            href="/generate"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors"
          >
            Generate Custom Worksheet
          </Link>
          <Link 
            href="/past-papers"
            className="inline-block bg-gray-800 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors border border-gray-700"
          >
            Browse Past Papers
          </Link>
        </div>
      </section>

      {/* Interactive Section */}
      <section className="mb-12">
        <p className="text-center text-gray-400 text-sm mb-4">
          Catch your worries - click on them!
        </p>
        <LazyWorryCatcher />
      </section>

      {/* Features Section - Keyword-Rich */}
      <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          Everything You Need for Edexcel Exam Success
        </h2>
        <p className="text-gray-400 text-center max-w-2xl mx-auto mb-12">
          From past papers to custom worksheets — GradeMax is the ultimate free revision tool for Edexcel IGCSE and A Level students.
        </p>
        
        <div className="grid md:grid-cols-3 gap-8">
          {/* Feature 1 - Worksheet Generator */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Custom Worksheet Generator</h3>
            <p className="text-gray-400">
              Create personalized Edexcel worksheets from real past paper questions. 
              Filter by topic, difficulty, and year range. Download as PDF with mark schemes included.
            </p>
            <Link href="/generate" className="text-blue-400 hover:text-blue-300 text-sm mt-3 inline-block">
              Generate Worksheet →
            </Link>
          </div>

          {/* Feature 2 - Topic-Wise Practice */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Topic-Wise Past Papers</h3>
            <p className="text-gray-400">
              Browse Edexcel past paper questions organized by topic and chapter. 
              Focus on weak areas with targeted practice from actual exam questions.
            </p>
            <Link href="/subjects" className="text-purple-400 hover:text-purple-300 text-sm mt-3 inline-block">
              Browse by Topic →
            </Link>
          </div>

          {/* Feature 3 - Mark Schemes */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Instant Mark Schemes</h3>
            <p className="text-gray-400">
              Every Edexcel past paper comes with its official mark scheme. 
              Check your answers instantly and understand the marking criteria.
            </p>
            <Link href="/past-papers" className="text-green-400 hover:text-green-300 text-sm mt-3 inline-block">
              View Past Papers →
            </Link>
          </div>
        </div>
      </section>

      {/* IGCSE Subjects Section */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="igcse-past-papers">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            Edexcel IGCSE Past Papers
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Free Pearson Edexcel International GCSE past papers organized by topic with mark schemes
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {igcseSubjects.map((subj) => (
              <Link 
                key={subj.slug}
                href={`/subjects/igcse/${subj.slug}`}
                className="bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-blue-600 transition-colors group"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg group-hover:text-blue-400 transition-colors">
                    IGCSE {subj.name}
                  </h3>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{subj.code}</span>
                </div>
                <p className="text-sm text-gray-400">
                  {subj.topics} topics · {subj.years} · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
          <div className="text-center mt-6">
            <Link href="/edexcel-igcse-past-papers" className="text-blue-400 hover:text-blue-300 text-sm">
              View all IGCSE past papers →
            </Link>
          </div>
        </div>
      </section>

      {/* A Level Subjects Section */}
      <section className="px-4 md:px-8 py-12" id="a-level-past-papers">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
            Edexcel A Level (IAL) Past Papers
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Free Pearson Edexcel International A Level past papers organized by topic with mark schemes
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {ialSubjects.map((subj) => (
              <Link 
                key={subj.slug}
                href={`/subjects/ial/${subj.slug}`}
                className="bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-purple-600 transition-colors group"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg group-hover:text-purple-400 transition-colors">
                    A Level {subj.name}
                  </h3>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{subj.code}</span>
                </div>
                <p className="text-sm text-gray-400">
                  {subj.topics} topics · {subj.years} · Mark schemes included
                </p>
              </Link>
            ))}
          </div>
          <div className="text-center mt-6">
            <Link href="/edexcel-a-level-past-papers" className="text-purple-400 hover:text-purple-300 text-sm">
              View all A Level past papers →
            </Link>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-8">
            How to Use GradeMax for Edexcel Exam Revision
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">1</div>
              <h3 className="font-semibold mb-2">Choose Your Subject</h3>
              <p className="text-sm text-gray-400">
                Select from IGCSE or A Level subjects — Physics, Maths, Chemistry, Biology, ICT, and more.
              </p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">2</div>
              <h3 className="font-semibold mb-2">Pick Topics &amp; Years</h3>
              <p className="text-sm text-gray-400">
                Browse topic-wise questions or filter by year. Choose specific chapters to focus your revision.
              </p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">3</div>
              <h3 className="font-semibold mb-2">Generate &amp; Practice</h3>
              <p className="text-sm text-gray-400">
                Generate a custom worksheet PDF or practice online. Check answers with official mark schemes instantly.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-4 md:px-8 py-16 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Start Revising with Edexcel Past Papers Today
        </h2>
        <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
          Join thousands of students using GradeMax to prepare for their Edexcel IGCSE and A Level exams. 
          Generate custom worksheets, practice topic-wise questions, and access mark schemes — completely free.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link 
            href="/generate"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors"
          >
            Generate Custom Worksheet
          </Link>
          <Link 
            href="/browse"
            className="inline-block bg-gray-800 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors border border-gray-700"
          >
            Browse All Questions
          </Link>
        </div>
      </section>

      {/* Trust Signals */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-xl font-semibold mb-8 text-gray-300">
            Trusted by Students Worldwide
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-3xl font-bold text-blue-500">1000+</p>
              <p className="text-gray-400 text-sm">Past Paper Questions</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-purple-500">14+</p>
              <p className="text-gray-400 text-sm">Years of Papers</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-green-500">9</p>
              <p className="text-gray-400 text-sm">Edexcel Subjects</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-amber-500">Free</p>
              <p className="text-gray-400 text-sm">No Cost Ever</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section - Critical for SEO Rich Snippets */}
      <section className="px-4 md:px-8 py-12" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-8">
            Frequently Asked Questions About Edexcel Past Papers
          </h2>
          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <details key={idx} className="bg-gray-900 rounded-lg border border-gray-800 group">
                <summary className="px-6 py-4 cursor-pointer font-semibold text-gray-200 hover:text-white transition-colors list-none flex justify-between items-center">
                  {faq.q}
                  <svg className="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform flex-shrink-0 ml-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p className="px-6 pb-4 text-gray-400 text-sm leading-relaxed">
                  {faq.a}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* SEO Content Footer - Long-tail Keywords */}
      <section className="px-4 md:px-8 py-12 bg-gray-950 border-t border-gray-800">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-lg font-semibold mb-4 text-gray-300">
            Edexcel Past Papers &amp; Resources on GradeMax
          </h2>
          <div className="grid md:grid-cols-2 gap-8 text-sm text-gray-500">
            <div>
              <h3 className="text-gray-400 font-medium mb-2">IGCSE Past Papers</h3>
              <ul className="space-y-1">
                <li><Link href="/subjects/igcse/physics" className="hover:text-gray-300">Edexcel IGCSE Physics Past Papers (4PH1)</Link></li>
                <li><Link href="/subjects/igcse/maths-a" className="hover:text-gray-300">Edexcel IGCSE Maths A Past Papers (4MA1)</Link></li>
                <li><Link href="/subjects/igcse/maths-b" className="hover:text-gray-300">Edexcel IGCSE Maths B Past Papers (4MB1)</Link></li>
                <li><Link href="/subjects/igcse/chemistry" className="hover:text-gray-300">Edexcel IGCSE Chemistry Past Papers (4CH1)</Link></li>
                <li><Link href="/subjects/igcse/biology" className="hover:text-gray-300">Edexcel IGCSE Biology Past Papers (4BI1)</Link></li>
                <li><Link href="/subjects/igcse/ict" className="hover:text-gray-300">Edexcel IGCSE ICT Past Papers (4IT1)</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-gray-400 font-medium mb-2">A Level Past Papers</h3>
              <ul className="space-y-1">
                <li><Link href="/subjects/ial/pure-maths-1" className="hover:text-gray-300">Edexcel A Level Pure Maths 1 Past Papers (WMA11)</Link></li>
                <li><Link href="/subjects/ial/mechanics-1" className="hover:text-gray-300">Edexcel A Level Mechanics 1 Past Papers (WME01)</Link></li>
                <li><Link href="/subjects/ial/statistics-1" className="hover:text-gray-300">Edexcel A Level Statistics 1 Past Papers (WST01)</Link></li>
              </ul>
              <h3 className="text-gray-400 font-medium mb-2 mt-4">Quick Links</h3>
              <ul className="space-y-1">
                <li><Link href="/generate" className="hover:text-gray-300">Custom Worksheet Generator</Link></li>
                <li><Link href="/browse" className="hover:text-gray-300">Browse All Questions</Link></li>
                <li><Link href="/subjects" className="hover:text-gray-300">All Subjects</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
