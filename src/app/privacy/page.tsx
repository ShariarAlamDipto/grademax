import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'GradeMax Privacy Policy - Learn how we collect, use, and protect your personal information.',
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-12">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Privacy Policy</h1>
        <p className="text-gray-400 mb-8">Last updated: February 2026</p>
        
        <div className="prose prose-invert max-w-none">
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Introduction</h2>
            <p className="text-gray-300 mb-4">
              GradeMax (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is committed to protecting your privacy. 
              This Privacy Policy explains how we collect, use, disclose, and safeguard your 
              information when you visit our website grademax.me.
            </p>
            <p className="text-gray-300">
              Please read this privacy policy carefully. If you do not agree with the terms 
              of this privacy policy, please do not access the site.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Information We Collect</h2>
            <h3 className="text-xl font-semibold mb-2">Information You Provide</h3>
            <p className="text-gray-300 mb-4">
              We may collect information you voluntarily provide when using our services, including:
            </p>
            <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
              <li>Email address (if you contact us or create an account)</li>
              <li>Feedback and correspondence</li>
              <li>Any other information you choose to provide</li>
            </ul>

            <h3 className="text-xl font-semibold mb-2">Automatically Collected Information</h3>
            <p className="text-gray-300 mb-4">
              When you access our website, we may automatically collect certain information, including:
            </p>
            <ul className="list-disc list-inside text-gray-300 space-y-2">
              <li>Browser type and version</li>
              <li>Operating system</li>
              <li>Pages visited and time spent</li>
              <li>Referring website</li>
              <li>Device information</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">How We Use Your Information</h2>
            <p className="text-gray-300 mb-4">
              We use the information we collect to:
            </p>
            <ul className="list-disc list-inside text-gray-300 space-y-2">
              <li>Provide, operate, and maintain our website</li>
              <li>Improve, personalize, and expand our services</li>
              <li>Understand and analyze how you use our website</li>
              <li>Develop new products, services, and features</li>
              <li>Communicate with you for customer service and support</li>
              <li>Send you updates and other information</li>
              <li>Find and prevent fraud</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Analytics</h2>
            <p className="text-gray-300">
              We use Vercel Analytics to collect anonymous usage data to help us understand 
              how visitors use our website. This data is aggregated and does not personally 
              identify you. We use this information to improve our services and user experience.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Cookies</h2>
            <p className="text-gray-300 mb-4">
              We may use cookies and similar tracking technologies to track activity on our 
              website and hold certain information. Cookies are files with small amounts of 
              data which may include an anonymous unique identifier.
            </p>
            <p className="text-gray-300">
              You can instruct your browser to refuse all cookies or to indicate when a 
              cookie is being sent. However, if you do not accept cookies, you may not 
              be able to use some portions of our service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Data Security</h2>
            <p className="text-gray-300">
              We implement appropriate technical and organizational security measures to 
              protect your personal information. However, please note that no method of 
              transmission over the Internet or electronic storage is 100% secure.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Third-Party Services</h2>
            <p className="text-gray-300">
              We may employ third-party companies and services to facilitate our service, 
              provide service on our behalf, or assist us in analyzing how our service is 
              used. These third parties have access to your information only to perform 
              these tasks on our behalf and are obligated not to disclose or use it for 
              any other purpose.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Children&apos;s Privacy</h2>
            <p className="text-gray-300">
              Our service is designed for students of all ages. We do not knowingly collect 
              personally identifiable information from children under 13 without parental 
              consent. If you are a parent or guardian and you are aware that your child 
              has provided us with personal information, please contact us.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Changes to This Policy</h2>
            <p className="text-gray-300">
              We may update our Privacy Policy from time to time. We will notify you of 
              any changes by posting the new Privacy Policy on this page and updating the 
              &quot;Last updated&quot; date.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">Contact Us</h2>
            <p className="text-gray-300">
              If you have any questions about this Privacy Policy, please contact us at{' '}
              <a href="mailto:privacy@grademax.me" className="text-blue-500 hover:text-blue-400">
                privacy@grademax.me
              </a>
            </p>
          </section>
        </div>
      </div>
    </main>
  )
}
