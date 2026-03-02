// src/app/page.tsx
import LazyWorryCatcher from "@/components/LazyWorryCatcher"
import Link from "next/link"

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white">
      {/* Hero Section */}
      <section className="text-center px-4 md:px-8 pt-8 md:pt-16">
        <h1 className="text-3xl md:text-5xl font-bold text-white mb-4">
          GradeMax - Your AI-Powered Study Assistant for IGCSE & A Level Success
        </h1>
        <p className="text-lg md:text-xl text-gray-300 max-w-3xl mx-auto mb-8">
          GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, 
          and ace your Cambridge and Edexcel exams with smart revision tools.
        </p>
      </section>

      {/* Interactive Section */}
      <section className="mb-12">
        <p className="text-center text-gray-400 text-sm mb-4">
          Catch your worries - click on them!
        </p>
        <LazyWorryCatcher />
      </section>

      {/* Features Section */}
      <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-12">
          Everything You Need to Excel in Your Exams
        </h2>
        
        <div className="grid md:grid-cols-3 gap-8">
          {/* Feature 1 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Custom Worksheet Generator</h3>
            <p className="text-gray-400">
              Create personalized worksheets from years of past papers. Filter by topic, 
              difficulty, and year range to focus on exactly what you need.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Topic-Wise Practice</h3>
            <p className="text-gray-400">
              Browse questions organized by topic. Master each concept with targeted 
              practice from actual exam questions with mark schemes included.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Smart Revision</h3>
            <p className="text-gray-400">
              Track your progress, identify weak areas, and get instant access to 
              mark schemes. Study smarter, not harder.
            </p>
          </div>
        </div>
      </section>

      {/* Subjects Section */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-8">
            Subjects We Cover
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">Mathematics</p>
              <p className="text-sm text-gray-400">IGCSE & A Level</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">Physics</p>
              <p className="text-sm text-gray-400">IGCSE & A Level</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">Further Maths</p>
              <p className="text-sm text-gray-400">A Level</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">More Coming</p>
              <p className="text-sm text-gray-400">Chemistry, Biology...</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-4 md:px-8 py-16 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Ready to Boost Your Grades?
        </h2>
        <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
          Join thousands of students using GradeMax to prepare for their IGCSE and A Level exams. 
          Start generating custom worksheets today - completely free.
        </p>
        <Link 
          href="/generate"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors"
        >
          Start Generating Worksheets
        </Link>
      </section>

      {/* Trust Signals */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-xl font-semibold mb-8 text-gray-300">
            Built for Students, By Students
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <p className="text-3xl font-bold text-blue-500">1000+</p>
              <p className="text-gray-400">Past Paper Questions</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-purple-500">14+</p>
              <p className="text-gray-400">Years of Papers</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-green-500">Free</p>
              <p className="text-gray-400">No Cost to Use</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
