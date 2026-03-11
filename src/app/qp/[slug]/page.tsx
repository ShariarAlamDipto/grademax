import { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { seoSubjects, type SEOSubject } from '@/lib/seo-subjects'
import { 
  generateOrganizationSchema, 
  generateBreadcrumbSchema,
  generateWebPageSchema,
  generateFAQSchema,
  generateCourseSchema,
  generateLearningResourceSchema,
} from '@/lib/seo-schema'

// Build a mapping of URL slugs to subjects  
// We support multiple slug patterns for maximum SEO coverage:
// /qp/igcse-physics, /qp/igcse-maths-a, /qp/a-level-pure-mathematics-1, etc.
function getSlugMapping(): Record<string, SEOSubject> {
  const map: Record<string, SEOSubject> = {}
  for (const subject of seoSubjects) {
    const levelPrefix = subject.level === 'igcse' ? 'igcse' : 'a-level'
    // Primary slug: /qp/igcse-physics
    map[`${levelPrefix}-${subject.slug}`] = subject
    // With "past-papers": /qp/igcse-physics-past-papers
    map[`${levelPrefix}-${subject.slug}-past-papers`] = subject
    // With "question-papers": /qp/igcse-physics-question-papers  
    map[`${levelPrefix}-${subject.slug}-question-papers`] = subject
    // Exam code: /qp/4ph1
    map[subject.examCode.toLowerCase()] = subject
    // Exam code with past papers: /qp/4ph1-past-papers
    map[`${subject.examCode.toLowerCase()}-past-papers`] = subject
  }
  return map
}

const slugMap = getSlugMapping()

export async function generateStaticParams() {
  return Object.keys(slugMap).map(slug => ({ slug }))
}

type PageProps = {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const subject = slugMap[slug]
  if (!subject) return {}

  const levelDisplay = subject.levelDisplay
  const isQP = slug.includes('question-papers')
  const isPP = slug.includes('past-papers') || !isQP

  const titlePrefix = isPP 
    ? `Edexcel ${levelDisplay} ${subject.name} Past Papers`
    : `Edexcel ${levelDisplay} ${subject.name} Question Papers`
  
  const title = `${titlePrefix} – Free Download with Mark Schemes (${subject.examCode})`
  const description = `Download free Edexcel ${levelDisplay} ${subject.name} (${subject.examCode}) past papers and mark schemes from ${subject.yearsAvailable[0]} to ${subject.yearsAvailable[subject.yearsAvailable.length - 1]}. ${subject.topics.length} topics covered. Practice topic-wise questions and generate custom worksheets.`

  return {
    title,
    description,
    keywords: [
      `${levelDisplay} ${subject.name} past papers`,
      `Edexcel ${subject.name} past papers`,
      `${subject.examCode} past papers`,
      `${levelDisplay} ${subject.name} question papers`,
      `${subject.name} past papers with mark schemes`,
      `Edexcel ${levelDisplay} ${subject.name}`,
      `${subject.name} revision`,
      `${subject.name} topic wise questions`,
      `${subject.examCode} mark scheme`,
      `free ${subject.name} past papers`,
      `${levelDisplay} ${subject.name} ${subject.yearsAvailable[subject.yearsAvailable.length - 1]}`,
      ...subject.keywords,
    ],
    openGraph: {
      title,
      description,
      url: `https://grademax.me/qp/${slug}`,
      siteName: 'GradeMax',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: `${titlePrefix} | GradeMax`,
      description: `Free ${levelDisplay} ${subject.name} past papers with mark schemes.`,
    },
    alternates: {
      canonical: `https://grademax.me/qp/${slug}`,
    },
  }
}

export default async function SubjectQPPage({ params }: PageProps) {
  const { slug } = await params
  const subject = slugMap[slug]
  if (!subject) notFound()

  const baseUrl = 'https://grademax.me'
  const levelDisplay = subject.levelDisplay

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateCourseSchema(subject),
      generateLearningResourceSchema(subject),
      generateFAQSchema(subject.faqs),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: `Edexcel Past Papers`, url: `${baseUrl}/edexcel-past-papers` },
        { name: `${levelDisplay} ${subject.name}`, url: `${baseUrl}/qp/${slug}` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/qp/${slug}`,
        `Edexcel ${levelDisplay} ${subject.name} Past Papers`,
        `Free Edexcel ${levelDisplay} ${subject.name} (${subject.examCode}) past papers with mark schemes.`
      ),
      // CollectionPage schema — strong signal for Google
      {
        '@type': 'CollectionPage',
        name: `Edexcel ${levelDisplay} ${subject.name} Past Papers Collection`,
        description: `Complete collection of Edexcel ${levelDisplay} ${subject.name} (${subject.examCode}) past papers from ${subject.yearsAvailable[0]} to ${subject.yearsAvailable[subject.yearsAvailable.length - 1]}.`,
        url: `${baseUrl}/qp/${slug}`,
        isPartOf: { '@id': `${baseUrl}/#website` },
        about: {
          '@type': 'Course',
          name: `${levelDisplay} ${subject.name}`,
          provider: { '@type': 'Organization', name: 'Pearson Edexcel' },
          courseCode: subject.examCode,
        },
        hasPart: subject.topics.map(topic => ({
          '@type': 'LearningResource',
          name: `${topic.name} - ${levelDisplay} ${subject.name}`,
          url: `${baseUrl}/subjects/${subject.level}/${subject.slug}/${topic.slug}`,
          learningResourceType: 'Past Paper Questions',
          educationalLevel: levelDisplay,
        })),
      },
    ]
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      
      {/* Breadcrumb */}
      <nav className="max-w-6xl mx-auto px-4 py-4 text-sm text-gray-400">
        <ol className="flex items-center gap-2 flex-wrap">
          <li><Link href="/" className="hover:text-white">Home</Link></li>
          <li>/</li>
          <li><Link href="/edexcel-past-papers" className="hover:text-white">Edexcel Past Papers</Link></li>
          <li>/</li>
          <li className="text-white">{levelDisplay} {subject.name}</li>
        </ol>
      </nav>

      {/* Hero */}
      <section className="px-4 md:px-8 pt-4 pb-12 max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <span className="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-sm font-medium">
            {subject.examBoard}
          </span>
          <span className="bg-gray-800 text-gray-300 px-3 py-1 rounded-full text-sm">
            {subject.examCode}
          </span>
          <span className="bg-green-900/30 text-green-400 px-3 py-1 rounded-full text-sm">
            Free
          </span>
        </div>

        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Edexcel {levelDisplay} {subject.name} Past Papers
        </h1>

        <p className="text-lg text-gray-300 max-w-4xl mb-3">
          {subject.longDescription}
        </p>
        <p className="text-sm text-gray-500 mb-8">
          {subject.yearsAvailable.length} years of papers ({subject.yearsAvailable[0]}–{subject.yearsAvailable[subject.yearsAvailable.length - 1]}) · {subject.topics.length} topics · Mark schemes included · Free download
        </p>

        <div className="flex flex-wrap gap-4">
          <Link 
            href={`/subjects/${subject.level}/${subject.slug}`}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Browse by Topic
          </Link>
          <Link 
            href={`/generate`}
            className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors border border-gray-700"
          >
            Generate Worksheet
          </Link>
          <Link 
            href={`/past-papers/${subject.slug}`}
            className="border border-gray-700 hover:border-gray-500 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Papers by Year
          </Link>
        </div>
      </section>

      {/* Topics Grid */}
      <section className="px-4 md:px-8 py-12 bg-gray-950">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">
            {levelDisplay} {subject.name} Topics
          </h2>
          <p className="text-gray-400 mb-8 text-sm">
            Practice topic-wise Edexcel {levelDisplay} {subject.name} past paper questions with mark schemes
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {subject.topics.map((topic, index) => (
              <Link
                key={topic.code}
                href={`/subjects/${subject.level}/${subject.slug}/${topic.slug}`}
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
                    <p className="text-gray-400 text-sm mt-1">{topic.description}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Past Papers by Year */}
      <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold mb-6">
          {levelDisplay} {subject.name} Past Papers by Year
        </h2>
        <div className="flex flex-wrap gap-3">
          {[...subject.yearsAvailable].reverse().map(year => (
            <Link
              key={year}
              href={`/past-papers/${subject.level}/${subject.slug}/${year}`}
              className="bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-lg px-4 py-2 text-sm transition-colors"
            >
              {subject.name} {year}
            </Link>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="px-4 md:px-8 py-12 bg-gray-950" id="faq">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-8">
            {levelDisplay} {subject.name} — Frequently Asked Questions
          </h2>
          <div className="space-y-3">
            {subject.faqs.map((faq, idx) => (
              <details key={idx} className="bg-gray-900 rounded-lg border border-gray-800 group">
                <summary className="px-5 py-4 cursor-pointer font-medium text-gray-200 hover:text-white transition-colors list-none flex justify-between items-center">
                  {faq.question}
                  <svg className="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform flex-shrink-0 ml-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p className="px-5 pb-4 text-gray-400 text-sm leading-relaxed">{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Related Subjects */}
      <section className="px-4 md:px-8 py-10 border-t border-gray-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-lg font-semibold mb-6 text-gray-300">Other {levelDisplay} Subjects</h2>
          <div className="flex flex-wrap justify-center gap-3">
            {seoSubjects
              .filter(s => s.level === subject.level && s.slug !== subject.slug)
              .map(s => {
                const prefix = s.level === 'igcse' ? 'igcse' : 'a-level'
                return (
                  <Link 
                    key={s.slug}
                    href={`/qp/${prefix}-${s.slug}`}
                    className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm text-gray-300 transition-colors"
                  >
                    {s.levelDisplay} {s.name}
                  </Link>
                )
              })}
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs text-gray-500">
            <Link href="/edexcel-past-papers" className="hover:text-white transition-colors">All Edexcel Past Papers</Link>
            <span>·</span>
            <Link href="/edexcel-igcse-past-papers" className="hover:text-white transition-colors">IGCSE Past Papers</Link>
            <span>·</span>
            <Link href="/edexcel-a-level-past-papers" className="hover:text-white transition-colors">A Level Past Papers</Link>
            <span>·</span>
            <Link href="/edexcel-worksheets" className="hover:text-white transition-colors">Worksheet Generator</Link>
          </div>
        </div>
      </section>
    </main>
  )
}
