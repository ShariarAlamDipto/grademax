import { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { 
  getSubjectsByLevel, 
  getLevelDisplay,
  type Level 
} from '@/lib/seo-subjects'
import { 
  generateOrganizationSchema, 
  generateBreadcrumbSchema,
  generateWebPageSchema,
  generateItemListSchema
} from '@/lib/seo-schema'

interface PageProps {
  params: Promise<{ level: string }>
}

const validLevels = ['igcse', 'ial'] as const

function isValidLevel(level: string): level is Level {
  return validLevels.includes(level as Level)
}

export async function generateStaticParams() {
  return validLevels.map(level => ({ level }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const resolvedParams = await params
  const { level } = resolvedParams
  
  if (!isValidLevel(level)) return {}
  
  const levelDisplay = getLevelDisplay(level)
  const subjects = getSubjectsByLevel(level)
  const subjectNames = subjects.map(s => s.name).join(', ')
  
  return {
    title: `${levelDisplay} Subjects – Past Papers & Study Resources | GradeMax`,
    description: `Master ${levelDisplay} with GradeMax. Access past papers, topic questions, and practice for ${subjectNames}. Free study resources for exam success.`,
    keywords: [
      `${levelDisplay} past papers`,
      `${levelDisplay} revision`,
      `${levelDisplay} study resources`,
      ...subjects.flatMap(s => s.keywords.slice(0, 2))
    ],
    openGraph: {
      title: `${levelDisplay} Subjects – Past Papers & Study Resources | GradeMax`,
      description: `Master ${levelDisplay} with GradeMax. Access past papers for ${subjectNames}.`,
      url: `https://grademax.me/subjects/${level}`,
      siteName: 'GradeMax',
      type: 'website',
    },
    alternates: {
      canonical: `https://grademax.me/subjects/${level}`,
    },
  }
}

export default async function LevelPage({ params }: PageProps) {
  const resolvedParams = await params
  const { level } = resolvedParams
  
  if (!isValidLevel(level)) {
    notFound()
  }
  
  const levelDisplay = getLevelDisplay(level)
  const subjects = getSubjectsByLevel(level)
  
  // Generate JSON-LD schema
  const baseUrl = 'https://grademax.me'
  const pageUrl = `${baseUrl}/subjects/${level}`
  
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: levelDisplay, url: pageUrl },
      ]),
      generateWebPageSchema(
        pageUrl,
        `${levelDisplay} Subjects – Past Papers & Study Resources`,
        `Master ${levelDisplay} with GradeMax. Access past papers and study resources.`
      ),
      generateItemListSchema(
        `${levelDisplay} Subjects`,
        subjects.map((s, i) => ({
          name: s.name,
          url: `${baseUrl}/subjects/${level}/${s.slug}`,
          position: i + 1
        }))
      )
    ]
  }
  
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      
      <main className="min-h-screen bg-black text-white">
        {/* Breadcrumb */}
        <nav className="max-w-6xl mx-auto px-4 py-4 text-sm text-gray-400">
          <ol className="flex items-center gap-2">
            <li><Link href="/" className="hover:text-white">Home</Link></li>
            <li>/</li>
            <li className="text-white">{levelDisplay}</li>
          </ol>
        </nav>
        
        {/* Hero */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            {levelDisplay} Subjects
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mb-8">
            Master {levelDisplay} with GradeMax. Choose a subject below to access 
            past papers, topic-wise questions, and practice tools.
          </p>
          
          {/* Subject Stats */}
          <div className="flex gap-8 text-sm text-gray-400 mb-12">
            <div>
              <span className="text-2xl font-bold text-white">{subjects.length}</span>
              <span className="ml-2">Subjects</span>
            </div>
            <div>
              <span className="text-2xl font-bold text-white">
                {subjects.reduce((acc, s) => acc + s.topics.length, 0)}
              </span>
              <span className="ml-2">Topics</span>
            </div>
            <div>
              <span className="text-2xl font-bold text-white">
                {subjects.reduce((acc, s) => acc + s.yearsAvailable.length, 0)}+
              </span>
              <span className="ml-2">Paper Years</span>
            </div>
          </div>
        </section>
        
        {/* Subjects Grid */}
        <section className="px-4 md:px-8 py-8 max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold mb-8">Choose Your Subject</h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {subjects.map(subject => (
              <Link 
                key={subject.slug}
                href={`/subjects/${level}/${subject.slug}`}
                className="group bg-gray-900 rounded-xl p-6 border border-gray-800 hover:border-gray-600 transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold group-hover:text-blue-400 transition-colors">
                      {subject.name}
                    </h3>
                    <p className="text-sm text-gray-500">{subject.examBoard} • {subject.examCode}</p>
                  </div>
                </div>
                
                <p className="text-gray-400 text-sm mb-4">
                  {subject.shortDescription}
                </p>
                
                <div className="flex gap-4 text-xs text-gray-500">
                  <span>{subject.topics.length} topics</span>
                  <span>•</span>
                  <span>{subject.yearsAvailable.length} years of papers</span>
                </div>
                
                {/* Topic preview */}
                <div className="mt-4 pt-4 border-t border-gray-800">
                  <p className="text-xs text-gray-500 mb-2">Topics include:</p>
                  <div className="flex flex-wrap gap-1">
                    {subject.topics.slice(0, 4).map(topic => (
                      <span 
                        key={topic.code}
                        className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded"
                      >
                        {topic.name}
                      </span>
                    ))}
                    {subject.topics.length > 4 && (
                      <span className="text-xs text-gray-500">
                        +{subject.topics.length - 4} more
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
        
        {/* CTA Section */}
        <section className="px-4 md:px-8 py-16 max-w-6xl mx-auto">
          <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 rounded-2xl p-8 md:p-12 text-center">
            <h2 className="text-2xl md:text-3xl font-bold mb-4">
              Ready to Start Practicing?
            </h2>
            <p className="text-gray-300 mb-8 max-w-2xl mx-auto">
              Generate custom worksheets from real past papers, practice by topic, 
              and track your progress with GradeMax.
            </p>
            <div className="flex justify-center gap-4">
              <Link 
                href="/generate"
                className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors"
              >
                Generate Worksheet
              </Link>
              <Link 
                href="/browse"
                className="bg-gray-800 hover:bg-gray-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors"
              >
                Browse Questions
              </Link>
            </div>
          </div>
        </section>
        
        {/* FAQ Section for SEO */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold mb-8">Frequently Asked Questions</h2>
          <div className="space-y-6">
            <div className="bg-gray-900 rounded-lg p-6">
              <h3 className="font-semibold mb-2">What is {levelDisplay}?</h3>
              <p className="text-gray-400">
                {level === 'igcse' 
                  ? 'IGCSE (International General Certificate of Secondary Education) is a globally recognized qualification for 14-16 year old students. It provides excellent preparation for A Levels and is accepted by universities worldwide.'
                  : 'IAL (International Advanced Level) is the international version of A Levels, typically taken by 16-19 year old students. It is equivalent to UK A Levels and is accepted by universities globally for undergraduate admissions.'
                }
              </p>
            </div>
            <div className="bg-gray-900 rounded-lg p-6">
              <h3 className="font-semibold mb-2">How can GradeMax help me with {levelDisplay}?</h3>
              <p className="text-gray-400">
                GradeMax provides access to past papers organized by topic, worksheet generation, 
                and instant mark schemes. Practice exactly what you need to improve your grades.
              </p>
            </div>
            <div className="bg-gray-900 rounded-lg p-6">
              <h3 className="font-semibold mb-2">Are the past papers free?</h3>
              <p className="text-gray-400">
                Yes! GradeMax provides free access to organized past paper questions. 
                Generate custom worksheets and practice anytime.
              </p>
            </div>
          </div>
        </section>
      </main>
    </>
  )
}
