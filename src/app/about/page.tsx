import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'About Us',
  description: 'Learn about GradeMax - the AI-powered study assistant helping IGCSE and A Level students prepare for exams with custom worksheets and past paper practice.',
}

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-12">
        <h1 className="text-3xl md:text-4xl font-bold mb-8">About GradeMax</h1>
        
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Our Mission</h2>
          <p className="text-gray-300 mb-4">
            GradeMax was created with one simple goal: to make exam preparation more efficient 
            and effective for IGCSE and A Level students worldwide. We believe every student 
            deserves access to quality study resources that help them achieve their academic goals.
          </p>
          <p className="text-gray-300">
            Our AI-powered platform transforms years of past examination papers into personalized 
            study materials, allowing students to focus on exactly what they need to improve.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">What We Offer</h2>
          <ul className="space-y-4 text-gray-300">
            <li className="flex items-start gap-3">
              <span className="text-blue-500 mt-1">✓</span>
              <div>
                <strong className="text-white">Custom Worksheet Generator</strong>
                <p>Create personalized practice papers filtered by topic, year, and difficulty level.</p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-blue-500 mt-1">✓</span>
              <div>
                <strong className="text-white">Topic-Wise Question Bank</strong>
                <p>Access thousands of past paper questions organized by subject and topic.</p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-blue-500 mt-1">✓</span>
              <div>
                <strong className="text-white">Instant Mark Schemes</strong>
                <p>Check your answers immediately with official mark schemes included.</p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-blue-500 mt-1">✓</span>
              <div>
                <strong className="text-white">Free Access</strong>
                <p>All core features are completely free - no hidden costs or subscriptions.</p>
              </div>
            </li>
          </ul>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Subjects We Cover</h2>
          <p className="text-gray-300 mb-4">
            We currently support the following subjects with more being added regularly:
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">Mathematics</p>
              <p className="text-sm text-gray-400">IGCSE & A Level</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">Physics</p>
              <p className="text-sm text-gray-400">IGCSE & A Level</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <p className="font-semibold">Further Mathematics</p>
              <p className="text-sm text-gray-400">A Level</p>
            </div>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Built by Students, for Students</h2>
          <p className="text-gray-300 mb-4">
            GradeMax was founded by students who experienced firsthand the challenges of 
            exam preparation. We understand the stress of deadlines, the overwhelm of revision, 
            and the need for efficient study tools.
          </p>
          <p className="text-gray-300">
            Our platform is designed to address these challenges by providing smart, 
            AI-powered tools that help you study smarter, not harder.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Contact Us</h2>
          <p className="text-gray-300">
            Have questions, feedback, or suggestions? We&apos;d love to hear from you. 
            Visit our <a href="/contact" className="text-blue-500 hover:text-blue-400">contact page</a> to 
            get in touch with our team.
          </p>
        </section>
      </div>
    </main>
  )
}
