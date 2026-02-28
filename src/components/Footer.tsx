import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="bg-gray-950 border-t border-gray-800">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
          {/* Company */}
          <div>
            <h3 className="font-semibold text-white mb-4">GradeMax</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/about" className="hover:text-white transition-colors">About Us</Link></li>
              <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
            </ul>
          </div>

          {/* Features */}
          <div>
            <h3 className="font-semibold text-white mb-4">Features</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/generate" className="hover:text-white transition-colors">Worksheet Generator</Link></li>
              <li><Link href="/browse" className="hover:text-white transition-colors">Browse Topics</Link></li>
              <li><Link href="/past-papers" className="hover:text-white transition-colors">Past Papers</Link></li>
            </ul>
          </div>

          {/* Subjects */}
          <div>
            <h3 className="font-semibold text-white mb-4">Subjects</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li>Mathematics</li>
              <li>Physics</li>
              <li>Further Maths</li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="font-semibold text-white mb-4">Legal</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-6 text-center text-sm text-gray-500">
          <p>© {new Date().getFullYear()} GradeMax. All rights reserved.</p>
          <p className="mt-2">Built for IGCSE & A Level students worldwide.</p>
        </div>
      </div>
    </footer>
  )
}
