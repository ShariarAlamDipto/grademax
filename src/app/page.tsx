// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import Link from "next/link"

const subjects = [
  { name: "Physics", level: "igcse", slug: "physics", code: "4PH1" },
  { name: "Maths A", level: "igcse", slug: "maths-a", code: "4MA1" },
  { name: "Maths B", level: "igcse", slug: "maths-b", code: "4MB1" },
  { name: "Chemistry", level: "igcse", slug: "chemistry", code: "4CH1" },
  { name: "Biology", level: "igcse", slug: "biology", code: "4BI1" },
  { name: "ICT", level: "igcse", slug: "ict", code: "4IT1" },
  { name: "Pure Maths 1", level: "ial", slug: "pure-mathematics-1", code: "WMA11" },
  { name: "Mechanics 1", level: "ial", slug: "mechanics-1", code: "WME01" },
  { name: "Statistics 1", level: "ial", slug: "statistics-1", code: "WST01" },
]

// SEO FAQs — collapsed by default, minimal visual footprint
const faqs = [
  { q: "Where can I find free Edexcel past papers?", a: "GradeMax offers free Edexcel IGCSE and A Level past papers for Physics, Maths, Chemistry, Biology, and ICT. All papers include mark schemes and are organized by topic and year from 2010–2025." },
  { q: "Can I practice Edexcel past papers by topic?", a: "Yes — all questions are organized by topic (chapter-wise). Browse a specific chapter like Electricity, Forces, Algebra, or Differentiation and practice with instant mark scheme access." },
  { q: "Is GradeMax free?", a: "Completely free. No sign-up required for browsing past papers and generating worksheets." },
  { q: "What subjects are available on GradeMax?", a: "GradeMax covers Edexcel IGCSE Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), ICT (4IT1), and A Level Pure Maths 1 (WMA11), Mechanics 1 (WME01), Statistics 1 (WST01)." },
  { q: "How do I generate custom worksheets from past papers?", a: "Use the free GradeMax Worksheet Generator — select your subject, pick topics, set difficulty and year range, then generate a custom PDF worksheet with its matching mark scheme in seconds." },
  { q: "Does GradeMax have Edexcel 2024 and 2025 past papers?", a: "Yes, GradeMax is regularly updated with the latest Edexcel past papers and mark schemes as they are released by Pearson." },
]

export default function Home() {
  const igcseSubjects = subjects.filter(s => s.level === "igcse")
  const ialSubjects = subjects.filter(s => s.level === "ial")

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-10 md:pt-20 pb-6">
        <h1 className="text-3xl md:text-5xl font-bold text-white mb-4">
          Free Edexcel Past Papers and Custom Worksheets
        </h1>
        <p className="hero-description text-lg text-gray-400 max-w-2xl mx-auto mb-3">
          IGCSE and A Level past papers organized by topic, with mark schemes. 
          Generate custom worksheets from real exam questions.
        </p>
        <p className="text-sm text-gray-500 max-w-xl mx-auto mb-8">
          Pearson Edexcel question papers from 2010–2025 · 9 subjects · Topic-wise &amp; year-wise
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/generate" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors">
            Generate Worksheet
          </Link>
          <Link href="/past-papers" className="bg-gray-800 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors border border-gray-700">
            Browse Past Papers
          </Link>
        </div>
      </section>

      {/* Worry Catcher */}
      <section className="mb-8">
        <p className="text-center text-gray-500 text-sm mb-4">Catch your worries - click on them!</p>
        <LazyWorryCatcher />
      </section>

      {/* IGCSE Subjects */}
      <section className="px-4 md:px-8 py-10 max-w-4xl mx-auto">
        <h2 className="text-xl md:text-2xl font-bold text-center mb-2">Edexcel IGCSE Past Papers</h2>
        <p className="text-gray-500 text-sm text-center mb-6">Free Pearson Edexcel International GCSE question papers with mark schemes</p>
        <div className="grid grid-cols-3 sm:grid-cols-3 gap-3">
          {igcseSubjects.map((s) => (
            <Link
              key={`${s.level}-${s.slug}`}
              href={`/subjects/${s.level}/${s.slug}`}
              className="bg-gray-900 rounded-lg px-4 py-3 text-center border border-gray-800 hover:border-blue-600 transition-colors"
            >
              <p className="font-medium text-sm">{s.name}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.code}</p>
            </Link>
          ))}
        </div>
        <div className="text-center mt-4">
          <Link href="/edexcel-igcse-past-papers" className="text-blue-400 hover:text-blue-300 text-xs">
            View all IGCSE past papers →
          </Link>
        </div>
      </section>

      {/* A Level Subjects */}
      <section className="px-4 md:px-8 pb-10 max-w-4xl mx-auto">
        <h2 className="text-xl md:text-2xl font-bold text-center mb-2">Edexcel A Level Past Papers</h2>
        <p className="text-gray-500 text-sm text-center mb-6">Free Pearson Edexcel International A Level (IAL) question papers with mark schemes</p>
        <div className="grid grid-cols-3 sm:grid-cols-3 gap-3">
          {ialSubjects.map((s) => (
            <Link
              key={`${s.level}-${s.slug}`}
              href={`/subjects/${s.level}/${s.slug}`}
              className="bg-gray-900 rounded-lg px-4 py-3 text-center border border-gray-800 hover:border-purple-600 transition-colors"
            >
              <p className="font-medium text-sm">{s.name}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.code}</p>
            </Link>
          ))}
        </div>
        <div className="text-center mt-4">
          <Link href="/edexcel-a-level-past-papers" className="text-purple-400 hover:text-purple-300 text-xs">
            View all A Level past papers →
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="px-4 md:px-8 py-8 bg-gray-950">
        <div className="max-w-3xl mx-auto flex justify-around text-center">
          <div>
            <p className="text-2xl font-bold text-blue-500">1000+</p>
            <p className="text-xs text-gray-500">Questions</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-purple-500">14+</p>
            <p className="text-xs text-gray-500">Years</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-500">9</p>
            <p className="text-xs text-gray-500">Subjects</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-amber-500">Free</p>
            <p className="text-xs text-gray-500">Always</p>
          </div>
        </div>
      </section>

      {/* About Edexcel Past Papers — SEO prose for word count + authoritative outbound links */}
      <section className="px-4 md:px-8 py-8 max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold text-center mb-4 text-gray-300">Why Practice with Edexcel Past Papers?</h2>
        <p className="text-sm text-gray-500 leading-relaxed mb-3">
          Past papers are the most effective way to prepare for{' '}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-gcses-and-edexcel-certificates.html" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-400 transition-colors">Pearson Edexcel IGCSE</a>{' '}
          and{' '}
          <a href="https://qualifications.pearson.com/en/qualifications/edexcel-international-advanced-levels.html" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-400 transition-colors">International A Level</a>{' '}
          examinations. By practising with real exam questions, students become familiar with the question styles, mark allocation, and timing required on exam day. Research consistently shows that retrieval practice — testing yourself with past papers rather than passively re-reading notes — leads to significantly better exam performance and long-term retention.
        </p>
        <p className="text-sm text-gray-500 leading-relaxed">
          GradeMax organizes every Edexcel past paper question by topic, so you can target your weak areas efficiently. Whether you&apos;re revising for IGCSE Physics, A Level Pure Maths, or any other subject, our topic-wise approach ensures you master each chapter before the exam. All questions come with official mark schemes so you can check your answers immediately and understand exactly what examiners are looking for.
        </p>
      </section>

      {/* How It Works — SEO-rich content without cluttering */}
      <section className="px-4 md:px-8 py-10 max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold text-center mb-6 text-gray-300">How to Use Edexcel Past Papers</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="font-medium text-sm text-white mb-2">1. Pick a Subject</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Choose from IGCSE or A Level subjects — Physics, Maths, Chemistry, Biology, ICT, or any unit.
            </p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="font-medium text-sm text-white mb-2">2. Practice by Topic</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Browse questions organized by topic. Focus on weak areas with real Edexcel exam questions and mark schemes.
            </p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="font-medium text-sm text-white mb-2">3. Generate Worksheets</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Create custom worksheets from past paper questions. Combine topics, set difficulty, download with mark schemes.
            </p>
          </div>
        </div>
      </section>

      {/* Popular Topics — Internal links for deep crawling */}
      <section className="px-4 md:px-8 py-8 bg-gray-950">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-lg font-semibold text-center mb-5 text-gray-300">Popular Edexcel Past Paper Topics</h2>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              { name: "Forces and Motion", href: "/subjects/igcse/physics/forces-and-motion" },
              { name: "Electricity", href: "/subjects/igcse/physics/electricity" },
              { name: "Algebra", href: "/subjects/igcse/maths-b/algebra" },
              { name: "Trigonometry", href: "/subjects/igcse/maths-b/trigonometry" },
              { name: "Organic Chemistry", href: "/subjects/igcse/chemistry/organic-chemistry" },
              { name: "Genetics", href: "/subjects/igcse/biology/reproduction-inheritance" },
              { name: "Differentiation", href: "/subjects/ial/pure-mathematics-1/differentiation" },
              { name: "SUVAT & Kinematics", href: "/subjects/ial/mechanics-1/kinematics" },
              { name: "Probability", href: "/subjects/ial/statistics-1/probability" },
              { name: "Waves", href: "/subjects/igcse/physics/waves" },
              { name: "Number", href: "/subjects/igcse/maths-a/number" },
              { name: "Geometry", href: "/subjects/igcse/maths-a/geometry" },
            ].map((t) => (
              <Link key={t.href} href={t.href} className="bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-full text-xs text-gray-400 hover:text-white transition-colors">
                {t.name}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ — compact, SEO value preserved */}
      <section className="px-4 md:px-8 py-8 max-w-2xl mx-auto" id="faq">
        <h2 className="text-lg font-semibold text-center mb-4 text-gray-300">Frequently Asked Questions</h2>
        <div className="space-y-2">
          {faqs.map((faq, idx) => (
            <details key={idx} className="bg-gray-900 rounded-lg border border-gray-800 group">
              <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-300 hover:text-white transition-colors list-none flex justify-between items-center">
                {faq.q}
                <svg className="w-4 h-4 text-gray-600 group-open:rotate-180 transition-transform flex-shrink-0 ml-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <p className="px-4 pb-3 text-gray-500 text-xs leading-relaxed">{faq.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* Related Resources — SEO internal linking */}
      <section className="px-4 md:px-8 py-8 bg-gray-950 border-t border-gray-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-sm font-semibold mb-4 text-gray-400">Quick Links</h2>
          <div className="flex flex-wrap justify-center gap-2">
            <Link href="/edexcel-past-papers" className="text-xs text-gray-500 hover:text-white transition-colors">Edexcel Past Papers</Link>
            <span className="text-gray-700">·</span>
            <Link href="/edexcel-igcse-past-papers" className="text-xs text-gray-500 hover:text-white transition-colors">IGCSE Past Papers</Link>
            <span className="text-gray-700">·</span>
            <Link href="/edexcel-a-level-past-papers" className="text-xs text-gray-500 hover:text-white transition-colors">A Level Past Papers</Link>
            <span className="text-gray-700">·</span>
            <Link href="/edexcel-worksheets" className="text-xs text-gray-500 hover:text-white transition-colors">Worksheet Generator</Link>
            <span className="text-gray-700">·</span>
            <Link href="/subjects" className="text-xs text-gray-500 hover:text-white transition-colors">All Subjects</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
