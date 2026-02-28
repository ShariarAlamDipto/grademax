import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'GradeMax Terms of Service - Read our terms and conditions for using the GradeMax study platform.',
}

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-12">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Terms of Service</h1>
        <p className="text-gray-400 mb-8">Last updated: February 2026</p>
        
        <div className="prose prose-invert max-w-none">
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Agreement to Terms</h2>
            <p className="text-gray-300 mb-4">
              By accessing or using GradeMax (grademax.me), you agree to be bound by these 
              Terms of Service and all applicable laws and regulations. If you do not agree 
              with any of these terms, you are prohibited from using or accessing this site.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Description of Service</h2>
            <p className="text-gray-300 mb-4">
              GradeMax provides an educational platform that allows students to:
            </p>
            <ul className="list-disc list-inside text-gray-300 space-y-2">
              <li>Generate custom worksheets from past examination papers</li>
              <li>Browse and practice topic-wise questions</li>
              <li>Access mark schemes for self-assessment</li>
              <li>Track study progress</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Use License</h2>
            <p className="text-gray-300 mb-4">
              Permission is granted to temporarily access the materials on GradeMax for 
              personal, non-commercial educational use only. This is the grant of a license, 
              not a transfer of title, and under this license you may not:
            </p>
            <ul className="list-disc list-inside text-gray-300 space-y-2">
              <li>Modify or copy the materials except for personal study purposes</li>
              <li>Use the materials for any commercial purpose</li>
              <li>Attempt to reverse engineer any software contained on GradeMax</li>
              <li>Remove any copyright or other proprietary notations from the materials</li>
              <li>Transfer the materials to another person or mirror the materials on any other server</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Educational Content</h2>
            <p className="text-gray-300 mb-4">
              The examination questions and mark schemes provided on GradeMax are sourced 
              from publicly available past papers. These materials are provided for 
              educational and revision purposes only.
            </p>
            <p className="text-gray-300">
              All examination content remains the intellectual property of the respective 
              examination boards (Cambridge Assessment International Education, Pearson 
              Edexcel, etc.). GradeMax does not claim ownership of this examination content.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">User Conduct</h2>
            <p className="text-gray-300 mb-4">
              When using GradeMax, you agree not to:
            </p>
            <ul className="list-disc list-inside text-gray-300 space-y-2">
              <li>Use the service for any unlawful purpose</li>
              <li>Attempt to gain unauthorized access to any part of the service</li>
              <li>Interfere with or disrupt the service or servers</li>
              <li>Share your account credentials with others</li>
              <li>Use automated systems or software to extract data from the service</li>
              <li>Redistribute or sell generated worksheets commercially</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Disclaimer</h2>
            <p className="text-gray-300 mb-4">
              The materials on GradeMax are provided on an &apos;as is&apos; basis. GradeMax makes 
              no warranties, expressed or implied, and hereby disclaims and negates all 
              other warranties including, without limitation, implied warranties or 
              conditions of merchantability, fitness for a particular purpose, or 
              non-infringement of intellectual property or other violation of rights.
            </p>
            <p className="text-gray-300">
              GradeMax does not guarantee that:
            </p>
            <ul className="list-disc list-inside text-gray-300 space-y-2 mt-2">
              <li>The service will meet your specific requirements</li>
              <li>The service will be uninterrupted, timely, secure, or error-free</li>
              <li>The results obtained from using the service will be accurate or reliable</li>
              <li>Using the materials will guarantee any particular examination results</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Limitations</h2>
            <p className="text-gray-300">
              In no event shall GradeMax or its suppliers be liable for any damages 
              (including, without limitation, damages for loss of data or profit, or 
              due to business interruption) arising out of the use or inability to use 
              the materials on GradeMax, even if GradeMax or a GradeMax authorized 
              representative has been notified orally or in writing of the possibility 
              of such damage.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Accuracy of Materials</h2>
            <p className="text-gray-300">
              The materials appearing on GradeMax could include technical, typographical, 
              or photographic errors. GradeMax does not warrant that any of the materials 
              on its website are accurate, complete or current. GradeMax may make changes 
              to the materials contained on its website at any time without notice.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Modifications</h2>
            <p className="text-gray-300">
              GradeMax may revise these terms of service at any time without notice. 
              By using this website you are agreeing to be bound by the then current 
              version of these terms of service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Governing Law</h2>
            <p className="text-gray-300">
              These terms and conditions are governed by and construed in accordance 
              with applicable laws and you irrevocably submit to the exclusive 
              jurisdiction of the courts in that location.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">Contact Information</h2>
            <p className="text-gray-300">
              If you have any questions about these Terms of Service, please contact us at{' '}
              <a href="mailto:legal@grademax.me" className="text-blue-500 hover:text-blue-400">
                legal@grademax.me
              </a>
            </p>
          </section>
        </div>
      </div>
    </main>
  )
}
