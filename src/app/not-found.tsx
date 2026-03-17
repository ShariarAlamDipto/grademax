import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Page Not Found',
  description: 'The page you are looking for does not exist. Browse free Edexcel IGCSE and A Level past papers on GradeMax.',
  robots: { index: false, follow: true },
}

export default function NotFound() {
  return (
    <main className="min-h-[60vh] flex flex-col items-center justify-center px-4 text-center bg-white dark:bg-black text-gray-900 dark:text-white">
      <h1 className="text-6xl font-bold text-gray-200 dark:text-gray-700 mb-4">404</h1>
      <h2 className="text-xl font-semibold text-gray-400 mb-2">Page Not Found</h2>
      <p className="text-gray-500 mb-8 max-w-md">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
        Try browsing our past papers or generating a worksheet instead.
      </p>

      <div className="flex flex-col sm:flex-row gap-3 mb-12">
        <Link
          href="/"
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
        >
          Go Home
        </Link>
        <Link
          href="/past-papers"
          className="bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-semibold px-6 py-3 rounded-lg transition-colors border border-gray-300 dark:border-gray-700"
        >
          Browse Past Papers
        </Link>
        <Link
          href="/generate"
          className="bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-semibold px-6 py-3 rounded-lg transition-colors border border-gray-300 dark:border-gray-700"
        >
          Generate Worksheet
        </Link>
      </div>

      {/* Internal links for SEO value */}
      <div className="max-w-2xl">
        <h3 className="text-sm font-semibold text-gray-500 mb-3">Popular Resources</h3>
        <div className="flex flex-wrap justify-center gap-2">
          <Link href="/subjects/igcse/physics" className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">IGCSE Physics</Link>
          <span className="text-gray-300 dark:text-gray-700">·</span>
          <Link href="/subjects/igcse/maths-a" className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">IGCSE Maths A</Link>
          <span className="text-gray-300 dark:text-gray-700">·</span>
          <Link href="/subjects/igcse/chemistry" className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">IGCSE Chemistry</Link>
          <span className="text-gray-300 dark:text-gray-700">·</span>
          <Link href="/subjects/igcse/biology" className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">IGCSE Biology</Link>
          <span className="text-gray-300 dark:text-gray-700">·</span>
          <Link href="/subjects/ial/pure-mathematics-1" className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">A Level Pure Maths 1</Link>
          <span className="text-gray-300 dark:text-gray-700">·</span>
          <Link href="/edexcel-past-papers" className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">All Edexcel Past Papers</Link>
        </div>
      </div>
    </main>
  )
}
