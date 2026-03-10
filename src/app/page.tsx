// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import Link from "next/link"

const subjects = [
  { name: "Physics", level: "igcse", slug: "physics" },
  { name: "Maths A", level: "igcse", slug: "maths-a" },
  { name: "Maths B", level: "igcse", slug: "maths-b" },
  { name: "Chemistry", level: "igcse", slug: "chemistry" },
  { name: "Biology", level: "igcse", slug: "biology" },
  { name: "ICT", level: "igcse", slug: "ict" },
  { name: "Pure Maths 1", level: "ial", slug: "pure-maths-1" },
  { name: "Mechanics 1", level: "ial", slug: "mechanics-1" },
  { name: "Statistics 1", level: "ial", slug: "statistics-1" },
]

// SEO FAQs — collapsed by default, minimal visual footprint
const faqs = [
  { q: "Where can I find free Edexcel past papers?", a: "GradeMax offers free Edexcel IGCSE and A Level past papers for Physics, Maths, Chemistry, Biology, and ICT. All papers include mark schemes and are organized by topic and year." },
  { q: "Can I practice past papers by topic?", a: "Yes — all questions are organized by topic. Browse a specific chapter and practice with instant mark scheme access." },
  { q: "Is GradeMax free?", a: "Completely free. No sign-up required for browsing past papers and generating worksheets." },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white">
      {/* Hero */}
      <section className="text-center px-4 md:px-8 pt-10 md:pt-20 pb-6">
        <h1 className="text-3xl md:text-5xl font-bold text-white mb-4">
          Free Edexcel Past Papers and Custom Worksheets
        </h1>
        <p className="hero-description text-lg text-gray-400 max-w-2xl mx-auto mb-8">
          IGCSE and A Level past papers organized by topic, with mark schemes. 
          Generate custom worksheets from real exam questions.
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

      {/* Subjects */}
      <section className="px-4 md:px-8 py-10 max-w-4xl mx-auto">
        <h2 className="text-xl md:text-2xl font-bold text-center mb-6">Subjects</h2>
        <div className="grid grid-cols-3 sm:grid-cols-3 md:grid-cols-3 gap-3">
          {subjects.map((s) => (
            <Link
              key={`${s.level}-${s.slug}`}
              href={`/subjects/${s.level}/${s.slug}`}
              className="bg-gray-900 rounded-lg px-4 py-3 text-center border border-gray-800 hover:border-blue-600 transition-colors"
            >
              <p className="font-medium text-sm">{s.name}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.level === "igcse" ? "IGCSE" : "A Level"}</p>
            </Link>
          ))}
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

      {/* FAQ — compact, SEO value preserved */}
      <section className="px-4 md:px-8 py-8 max-w-2xl mx-auto" id="faq">
        <h2 className="text-lg font-semibold text-center mb-4 text-gray-300">FAQ</h2>
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
    </main>
  )
}
