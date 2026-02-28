import { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { 
  getSubjectBySlug,
  seoSubjects,
  getLevelDisplay,
  type Level
} from '@/lib/seo-subjects'
import { generateTopicPageSchema } from '@/lib/seo-schema'

interface PageProps {
  params: Promise<{ level: string; slug: string; topic: string }>
}

const validLevels = ['igcse', 'ial'] as const

function isValidLevel(level: string): level is Level {
  return validLevels.includes(level as Level)
}

export async function generateStaticParams() {
  return seoSubjects.flatMap(subject =>
    subject.topics.map(topic => ({
      level: subject.level,
      slug: subject.slug,
      topic: topic.slug
    }))
  )
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const resolvedParams = await params
  const { level, slug, topic: topicSlug } = resolvedParams
  
  if (!isValidLevel(level)) return {}
  
  const subject = getSubjectBySlug(level, slug)
  if (!subject) return {}
  
  const topic = subject.topics.find(t => t.slug === topicSlug)
  if (!topic) return {}
  
  const title = `${topic.name} - ${subject.levelDisplay} ${subject.name} | GradeMax`
  const description = `Master ${topic.name} for ${subject.levelDisplay} ${subject.name}. ${topic.description} Practice with real exam questions and mark schemes.`
  
  return {
    title,
    description,
    keywords: [
      topic.name,
      `${subject.levelDisplay} ${topic.name}`,
      `${subject.name} ${topic.name}`,
      ...topic.keywords,
      ...subject.keywords.slice(0, 3)
    ],
    openGraph: {
      title,
      description,
      url: `https://grademax.me/subjects/${level}/${slug}/${topicSlug}`,
      siteName: 'GradeMax',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
    alternates: {
      canonical: `https://grademax.me/subjects/${level}/${slug}/${topicSlug}`,
    },
  }
}

export default async function TopicPage({ params }: PageProps) {
  const resolvedParams = await params
  const { level, slug, topic: topicSlug } = resolvedParams
  
  if (!isValidLevel(level)) {
    notFound()
  }
  
  const subject = getSubjectBySlug(level, slug)
  if (!subject) {
    notFound()
  }
  
  const topic = subject.topics.find(t => t.slug === topicSlug)
  if (!topic) {
    notFound()
  }
  
  const levelDisplay = getLevelDisplay(level)
  const schema = generateTopicPageSchema(subject, topic)
  
  // Find adjacent topics for navigation
  const topicIndex = subject.topics.findIndex(t => t.slug === topicSlug)
  const prevTopic = topicIndex > 0 ? subject.topics[topicIndex - 1] : null
  const nextTopic = topicIndex < subject.topics.length - 1 ? subject.topics[topicIndex + 1] : null
  
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
            <li><Link href={`/subjects/${level}/${slug}`} className="hover:text-white">{subject.name}</Link></li>
            <li>/</li>
            <li className="text-white">{topic.name}</li>
          </ol>
        </nav>
        
        {/* Hero Section */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <span className="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-sm font-medium">
              Topic {topic.code}
            </span>
            <span className="bg-gray-800 text-gray-300 px-3 py-1 rounded-full text-sm">
              {subject.levelDisplay} {subject.name}
            </span>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            {topic.name}
          </h1>
          
          <p className="text-xl text-gray-300 max-w-4xl mb-8">
            {topic.description} Master this topic with practice questions from real 
            {subject.levelDisplay} {subject.name} past papers.
          </p>
          
          {/* Keywords */}
          <div className="flex flex-wrap gap-2 mb-8">
            {topic.keywords.map(keyword => (
              <span 
                key={keyword}
                className="bg-gray-900 text-gray-300 px-3 py-1 rounded-full text-sm border border-gray-800"
              >
                {keyword}
              </span>
            ))}
          </div>
          
          {/* CTA Buttons */}
          <div className="flex flex-wrap gap-4">
            <Link 
              href={`/generate?subject=${slug}&level=${level}&topic=${topic.code}`}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              Practice {topic.name} Questions
            </Link>
            <Link 
              href={`/browse?subject=${slug}&topic=${topic.code}`}
              className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              Browse All Questions
            </Link>
          </div>
        </section>
        
        {/* What You'll Learn */}
        <section className="px-4 md:px-8 py-12 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-bold mb-8">
              What You&apos;ll Learn in {topic.name}
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              {topic.keywords.map((keyword, index) => (
                <div 
                  key={keyword}
                  className="bg-gray-900 rounded-lg p-5 border border-gray-800"
                >
                  <div className="flex items-start gap-4">
                    <div className="bg-green-600/20 text-green-400 w-8 h-8 rounded-lg flex items-center justify-center font-bold shrink-0">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="font-semibold capitalize">{keyword}</h3>
                      <p className="text-gray-400 text-sm mt-1">
                        Practice {keyword} questions from {subject.levelDisplay} {subject.name} exams.
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
        
        {/* Practice Section */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-8">
            Practice {topic.name} Questions
          </h2>
          
          <div className="bg-gray-900 rounded-xl p-8 border border-gray-800">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">
                Generate a Custom Worksheet
              </h3>
              <p className="text-gray-400 mb-6 max-w-lg mx-auto">
                Create a practice worksheet with {topic.name} questions from multiple years of 
                {subject.levelDisplay} {subject.name} past papers.
              </p>
              <Link 
                href={`/generate?subject=${slug}&level=${level}&topic=${topic.code}`}
                className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors"
              >
                Generate Worksheet
              </Link>
            </div>
          </div>
        </section>
        
        {/* Topic Navigation */}
        <section className="px-4 md:px-8 py-12 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-xl font-bold mb-6">More Topics in {subject.name}</h2>
            
            <div className="flex flex-wrap gap-2 mb-8">
              {subject.topics.map(t => (
                <Link
                  key={t.code}
                  href={`/subjects/${level}/${slug}/${t.slug}`}
                  className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                    t.slug === topicSlug
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-900 text-gray-300 hover:bg-gray-800 border border-gray-800'
                  }`}
                >
                  {t.name}
                </Link>
              ))}
            </div>
            
            {/* Prev/Next Navigation */}
            <div className="flex justify-between items-center pt-6 border-t border-gray-800">
              {prevTopic ? (
                <Link 
                  href={`/subjects/${level}/${slug}/${prevTopic.slug}`}
                  className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  <div className="text-left">
                    <div className="text-xs text-gray-500">Previous Topic</div>
                    <div className="font-medium">{prevTopic.name}</div>
                  </div>
                </Link>
              ) : <div />}
              
              {nextTopic ? (
                <Link 
                  href={`/subjects/${level}/${slug}/${nextTopic.slug}`}
                  className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-right"
                >
                  <div>
                    <div className="text-xs text-gray-500">Next Topic</div>
                    <div className="font-medium">{nextTopic.name}</div>
                  </div>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ) : <div />}
            </div>
          </div>
        </section>
        
        {/* Back to Subject CTA */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 rounded-2xl p-8 text-center">
            <h2 className="text-xl font-bold mb-4">
              Explore All {subject.name} Topics
            </h2>
            <p className="text-gray-300 mb-6">
              View all {subject.topics.length} topics in {subject.levelDisplay} {subject.name}
            </p>
            <Link 
              href={`/subjects/${level}/${slug}`}
              className="inline-block bg-white text-gray-900 px-6 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              View All Topics
            </Link>
          </div>
        </section>
      </main>
    </>
  )
}
