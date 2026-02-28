import { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { 
  getSubjectBySlug,
  seoSubjects,
  getLevelDisplay,
  type Level
} from '@/lib/seo-subjects'
import { generateSubjectPageSchema } from '@/lib/seo-schema'

interface PageProps {
  params: Promise<{ level: string; slug: string }>
}

const validLevels = ['igcse', 'ial'] as const

function isValidLevel(level: string): level is Level {
  return validLevels.includes(level as Level)
}

export async function generateStaticParams() {
  return seoSubjects.map(subject => ({
    level: subject.level,
    slug: subject.slug
  }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const resolvedParams = await params
  const { level, slug } = resolvedParams
  
  if (!isValidLevel(level)) return {}
  
  const subject = getSubjectBySlug(level, slug)
  if (!subject) return {}
  
  return {
    title: subject.metaTitle,
    description: subject.metaDescription,
    keywords: subject.keywords,
    openGraph: {
      title: subject.metaTitle,
      description: subject.metaDescription,
      url: `https://grademax.me/subjects/${level}/${slug}`,
      siteName: 'GradeMax',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: subject.metaTitle,
      description: subject.metaDescription,
    },
    alternates: {
      canonical: `https://grademax.me/subjects/${level}/${slug}`,
    },
  }
}

export default async function SubjectPage({ params }: PageProps) {
  const resolvedParams = await params
  const { level, slug } = resolvedParams
  
  if (!isValidLevel(level)) {
    notFound()
  }
  
  const subject = getSubjectBySlug(level, slug)
  if (!subject) {
    notFound()
  }
  
  const levelDisplay = getLevelDisplay(level)
  const schema = generateSubjectPageSchema(subject)
  
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      
      <main className="min-h-screen bg-black text-white">
        {/* Breadcrumb */}
        <nav className="max-w-6xl mx-auto px-4 py-4 text-sm text-gray-400">
          <ol className="flex items-center gap-2 flex-wrap">
            <li><Link href="/" className="hover:text-white">Home</Link></li>
            <li>/</li>
            <li><Link href={`/subjects/${level}`} className="hover:text-white">{levelDisplay}</Link></li>
            <li>/</li>
            <li className="text-white">{subject.name}</li>
          </ol>
        </nav>
        
        {/* Hero Section */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <span className="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-sm font-medium">
              {subject.examBoard}
            </span>
            <span className="bg-gray-800 text-gray-300 px-3 py-1 rounded-full text-sm">
              {subject.examCode}
            </span>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            {subject.h1}
          </h1>
          
          <p className="text-xl text-gray-300 max-w-4xl mb-8">
            {subject.longDescription}
          </p>
          
          {/* Quick Stats */}
          <div className="flex flex-wrap gap-6 text-sm mb-8">
            <div className="bg-gray-900 rounded-lg px-4 py-3">
              <span className="text-2xl font-bold text-white">{subject.topics.length}</span>
              <span className="ml-2 text-gray-400">Topics</span>
            </div>
            <div className="bg-gray-900 rounded-lg px-4 py-3">
              <span className="text-2xl font-bold text-white">{subject.yearsAvailable.length}</span>
              <span className="ml-2 text-gray-400">Years of Papers</span>
            </div>
            <div className="bg-gray-900 rounded-lg px-4 py-3">
              <span className="text-2xl font-bold text-white">{subject.yearsAvailable[0]}</span>
              <span className="mx-1 text-gray-500">-</span>
              <span className="text-2xl font-bold text-white">{subject.yearsAvailable[subject.yearsAvailable.length - 1]}</span>
              <span className="ml-2 text-gray-400">Coverage</span>
            </div>
          </div>
          
          {/* CTA Buttons */}
          <div className="flex flex-wrap gap-4">
            <Link 
              href={`/generate?subject=${slug}&level=${level}`}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              Generate Worksheet
            </Link>
            <Link 
              href={`/browse?subject=${slug}`}
              className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              Browse Questions
            </Link>
            <Link 
              href={`/past-papers/${level}/${slug}`}
              className="border border-gray-700 hover:border-gray-500 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              Past Papers
            </Link>
          </div>
        </section>
        
        {/* Topics Section */}
        <section className="px-4 md:px-8 py-12 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-bold mb-8">
              {subject.levelDisplay} {subject.name} Topics
            </h2>
            
            <div className="grid md:grid-cols-2 gap-4">
              {subject.topics.map((topic, index) => (
                <Link
                  key={topic.code}
                  href={`/subjects/${level}/${slug}/${topic.slug}`}
                  className="group bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-gray-600 transition-all"
                >
                  <div className="flex items-start gap-4">
                    <div className="bg-blue-600/20 text-blue-400 w-10 h-10 rounded-lg flex items-center justify-center font-bold shrink-0">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg group-hover:text-blue-400 transition-colors">
                        {topic.name}
                      </h3>
                      <p className="text-gray-400 text-sm mt-1">
                        {topic.description}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-3">
                        {topic.keywords.slice(0, 3).map(keyword => (
                          <span 
                            key={keyword}
                            className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
        
        {/* Past Papers by Year */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-8">
            Past Papers by Year
          </h2>
          
          <div className="flex flex-wrap gap-3">
            {subject.yearsAvailable.slice().reverse().map(year => (
              <Link
                key={year}
                href={`/past-papers/${level}/${slug}/${year}`}
                className="bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 px-4 py-2 rounded-lg transition-colors"
              >
                {year}
              </Link>
            ))}
          </div>
        </section>
        
        {/* FAQ Section */}
        <section className="px-4 md:px-8 py-12 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-bold mb-8">
              Frequently Asked Questions
            </h2>
            
            <div className="space-y-4">
              {subject.faqs.map((faq, index) => (
                <details 
                  key={index}
                  className="group bg-gray-900 rounded-lg border border-gray-800"
                >
                  <summary className="flex items-center justify-between p-5 cursor-pointer list-none">
                    <h3 className="font-semibold pr-4">{faq.question}</h3>
                    <svg 
                      className="w-5 h-5 text-gray-400 group-open:rotate-180 transition-transform" 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </summary>
                  <div className="px-5 pb-5 text-gray-400">
                    {faq.answer}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </section>
        
        {/* Related Subjects */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold mb-8">Related Subjects</h2>
          
          <div className="grid md:grid-cols-3 gap-4">
            {seoSubjects
              .filter(s => s.level === level && s.slug !== slug)
              .slice(0, 3)
              .map(relatedSubject => (
                <Link
                  key={relatedSubject.slug}
                  href={`/subjects/${level}/${relatedSubject.slug}`}
                  className="bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-gray-600 transition-all"
                >
                  <h3 className="font-semibold mb-2">{relatedSubject.name}</h3>
                  <p className="text-gray-400 text-sm">{relatedSubject.shortDescription}</p>
                </Link>
              ))}
          </div>
        </section>
        
        {/* Bottom CTA */}
        <section className="px-4 md:px-8 py-16 max-w-6xl mx-auto">
          <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 rounded-2xl p-8 md:p-12 text-center">
            <h2 className="text-2xl md:text-3xl font-bold mb-4">
              Start Practicing {subject.name} Now
            </h2>
            <p className="text-gray-300 mb-8 max-w-2xl mx-auto">
              Generate custom worksheets from real {subject.levelDisplay} {subject.name} past papers. 
              Focus on your weak topics and ace your exams.
            </p>
            <Link 
              href={`/generate?subject=${slug}&level=${level}`}
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-lg font-semibold text-lg transition-colors"
            >
              Generate Free Worksheet
            </Link>
          </div>
        </section>
      </main>
    </>
  )
}
