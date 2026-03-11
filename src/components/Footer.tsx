import Link from 'next/link'

import { useTheme } from '@/context/ThemeContext'

export default function Footer() {
  const { theme } = useTheme();
  const bg = theme === 'dark' ? 'bg-gray-950' : 'bg-white';
  const border = theme === 'dark' ? 'border-gray-800' : 'border-gray-200';
  const text = theme === 'dark' ? 'text-white' : 'text-gray-900';
  const muted = theme === 'dark' ? 'text-gray-400' : 'text-gray-500';
  return (
    <footer aria-label="Site footer" className={`${bg} border-t ${border}`}> 
      <div className="max-w-6xl mx-auto px-4 py-10">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-8">
          {/* Company */}
          <div>
            <h3 className="font-semibold text-white mb-4 text-sm">GradeMax</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/about" className="hover:text-white transition-colors">About Us</Link></li>
              <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
              <li><Link href="/edexcel-past-papers" className="hover:text-white transition-colors">Edexcel Past Papers</Link></li>
              <li><Link href="/edexcel-worksheets" className="hover:text-white transition-colors">Worksheet Generator</Link></li>
            </ul>
          </div>

          {/* IGCSE Past Papers */}
          <div>
            <h3 className="font-semibold text-white mb-4 text-sm">IGCSE Past Papers</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/subjects/igcse/physics" className="hover:text-white transition-colors">IGCSE Physics (4PH1)</Link></li>
              <li><Link href="/subjects/igcse/maths-a" className="hover:text-white transition-colors">IGCSE Maths A (4MA1)</Link></li>
              <li><Link href="/subjects/igcse/maths-b" className="hover:text-white transition-colors">IGCSE Maths B (4MB1)</Link></li>
              <li><Link href="/subjects/igcse/chemistry" className="hover:text-white transition-colors">IGCSE Chemistry (4CH1)</Link></li>
              <li><Link href="/subjects/igcse/biology" className="hover:text-white transition-colors">IGCSE Biology (4BI1)</Link></li>
              <li><Link href="/subjects/igcse/ict" className="hover:text-white transition-colors">IGCSE ICT (4IT1)</Link></li>
              <li><Link href="/edexcel-igcse-past-papers" className="hover:text-blue-400 text-blue-400/70 transition-colors text-xs mt-1 inline-block">View all IGCSE past papers →</Link></li>
            </ul>
          </div>

          {/* A Level Past Papers */}
          <div>
            <h3 className="font-semibold text-white mb-4 text-sm">A Level Past Papers</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/subjects/ial/pure-mathematics-1" className="hover:text-white transition-colors">Pure Maths 1 (WMA11)</Link></li>
              <li><Link href="/subjects/ial/mechanics-1" className="hover:text-white transition-colors">Mechanics 1 (WME01)</Link></li>
              <li><Link href="/subjects/ial/statistics-1" className="hover:text-white transition-colors">Statistics 1 (WST01)</Link></li>
              <li><Link href="/edexcel-a-level-past-papers" className="hover:text-purple-400 text-purple-400/70 transition-colors text-xs mt-1 inline-block">View all A Level past papers →</Link></li>
            </ul>
          </div>

          {/* Features */}
          <div>
            <h3 className="font-semibold text-white mb-4 text-sm">Features</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/generate" className="hover:text-white transition-colors">Custom Worksheet Generator</Link></li>
              <li><Link href="/browse" className="hover:text-white transition-colors">Browse by Topic</Link></li>
              <li><Link href="/past-papers" className="hover:text-white transition-colors">Past Papers by Year</Link></li>
              <li><Link href="/subjects" className="hover:text-white transition-colors">All Subjects</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="font-semibold text-white mb-4 text-sm">Legal</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
            </ul>
          </div>
        </div>

        {/* SEO-rich descriptive text — visible but minimal, helps crawlers */}
        <div className="border-t border-gray-800 pt-6 mb-6">
          <p className="text-xs text-gray-600 leading-relaxed max-w-4xl mx-auto text-center">
            GradeMax is a free platform for Edexcel IGCSE and A Level past papers, question papers, and mark schemes. 
            Practice topic-wise questions for Physics, Mathematics, Chemistry, Biology, and ICT. 
            Generate custom worksheets from real Pearson Edexcel exam papers. All resources are free — no sign-up required.
          </p>
        </div>

        <div className="border-t border-gray-800 pt-6 text-center text-sm text-gray-500">
          <p>© {new Date().getFullYear()} GradeMax. All rights reserved.</p>
          <p className="mt-2 text-xs text-gray-600">
            Free Edexcel past papers and custom worksheets for IGCSE &amp; A Level students worldwide.
          </p>
          <p className="mt-1 text-xs text-gray-700">
            Last updated: January 2025 · Papers available from 2010–2025
          </p>
        </div>
      </div>
    </footer>
  )
}
