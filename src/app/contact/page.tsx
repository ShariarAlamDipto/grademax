import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contact Us',
  description: 'Get in touch with the GradeMax team. We welcome your questions, feedback, and suggestions about our IGCSE and A Level study platform.',
}

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-12">
        <h1 className="text-3xl md:text-4xl font-bold mb-8">Contact Us</h1>
        
        <section className="mb-12">
          <p className="text-gray-300 mb-6">
            We&apos;d love to hear from you! Whether you have questions about our platform, 
            feedback on existing features, or suggestions for improvements, feel free to reach out.
          </p>
        </section>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Contact Information */}
          <section>
            <h2 className="text-2xl font-semibold mb-6">Get in Touch</h2>
            
            <div className="space-y-6">
              <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                <h3 className="font-semibold mb-2">Email Support</h3>
                <p className="text-gray-400 mb-2">For general inquiries and support:</p>
                <a href="mailto:support@grademax.me" className="text-blue-500 hover:text-blue-400">
                  support@grademax.me
                </a>
              </div>

              <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                <h3 className="font-semibold mb-2">Feature Requests</h3>
                <p className="text-gray-400 mb-2">Have an idea for a new feature?</p>
                <a href="mailto:feedback@grademax.me" className="text-blue-500 hover:text-blue-400">
                  feedback@grademax.me
                </a>
              </div>

              <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                <h3 className="font-semibold mb-2">Bug Reports</h3>
                <p className="text-gray-400 mb-2">Found something not working correctly?</p>
                <a href="mailto:bugs@grademax.me" className="text-blue-500 hover:text-blue-400">
                  bugs@grademax.me
                </a>
              </div>
            </div>
          </section>

          {/* FAQ Section */}
          <section>
            <h2 className="text-2xl font-semibold mb-6">Frequently Asked Questions</h2>
            
            <div className="space-y-4">
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                <h3 className="font-semibold mb-2">Is GradeMax free to use?</h3>
                <p className="text-gray-400 text-sm">
                  Yes! All core features including worksheet generation and topic-wise 
                  question browsing are completely free.
                </p>
              </div>

              <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                <h3 className="font-semibold mb-2">Which exam boards do you support?</h3>
                <p className="text-gray-400 text-sm">
                  We currently support Cambridge (CIE) and Edexcel past papers for 
                  IGCSE and A Level examinations.
                </p>
              </div>

              <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                <h3 className="font-semibold mb-2">How often do you add new papers?</h3>
                <p className="text-gray-400 text-sm">
                  We regularly update our database with the latest past papers as they 
                  become available after each examination session.
                </p>
              </div>

              <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                <h3 className="font-semibold mb-2">Can I request a new subject?</h3>
                <p className="text-gray-400 text-sm">
                  Absolutely! Send us an email at feedback@grademax.me with your subject 
                  request and we&apos;ll prioritize popular requests.
                </p>
              </div>
            </div>
          </section>
        </div>

        <section className="mt-12 bg-gray-900 rounded-xl p-8 border border-gray-800 text-center">
          <h2 className="text-xl font-semibold mb-4">Response Time</h2>
          <p className="text-gray-400">
            We typically respond to all inquiries within 24-48 hours during weekdays. 
            Thank you for your patience!
          </p>
        </section>
      </div>
    </main>
  )
}
