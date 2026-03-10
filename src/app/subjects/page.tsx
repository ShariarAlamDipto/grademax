import { Metadata } from 'next'
import Link from 'next/link'
import { seoSubjects, getSubjectsByLevel } from '@/lib/seo-subjects'
import { 
  generateOrganizationSchema, 
  generateBreadcrumbSchema,
  generateWebPageSchema
} from '@/lib/seo-schema'

export const metadata: Metadata = {
  title: 'All Edexcel Subjects – IGCSE & A Level Past Papers by Topic',
  description: 'Browse all Edexcel IGCSE and A Level subjects on GradeMax. Access topic-wise past papers, custom worksheets, and mark schemes for Physics, Maths, Chemistry, Biology, ICT and more.',
  keywords: [
    'Edexcel subjects', 'IGCSE subjects', 'A Level subjects',
    'Edexcel IGCSE past papers', 'Edexcel A Level past papers',
    'topic wise past papers', 'past papers by topic',
    'Edexcel exam revision', 'IGCSE revision', 'A Level revision',
    'study resources Edexcel', 'free past papers',
  ],
  openGraph: {
    title: 'All Edexcel Subjects – IGCSE & A Level Past Papers by Topic',
    description: 'Browse all Edexcel IGCSE and A Level subjects. Topic-wise past papers and custom worksheets.',
    url: 'https://grademax.me/subjects',
    siteName: 'GradeMax',
    type: 'website',
  },
  alternates: {
    canonical: 'https://grademax.me/subjects',
  },
}

export default function SubjectsIndexPage() {
  const igcseSubjects = getSubjectsByLevel('igcse')
  const ialSubjects = getSubjectsByLevel('ial')
  
  const baseUrl = 'https://grademax.me'
  
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateBreadcrumbSchema([
        { name: 'Home', url: baseUrl },
        { name: 'Subjects', url: `${baseUrl}/subjects` },
      ]),
      generateWebPageSchema(
        `${baseUrl}/subjects`,
        'All Subjects – IGCSE & A Level Past Papers',
        'Browse all IGCSE and A Level subjects on GradeMax.'
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
            <li className="text-white">Subjects</li>
          </ol>
        </nav>
        
        {/* Hero */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            All Subjects
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mb-8">
            Choose your qualification level and subject to access past papers, 
            topic-wise questions, and practice tools.
          </p>
          
          {/* Quick Stats */}
          <div className="flex gap-8 text-sm text-gray-400 mb-8">
            <div>
              <span className="text-2xl font-bold text-white">{seoSubjects.length}</span>
              <span className="ml-2">Subjects</span>
            </div>
            <div>
              <span className="text-2xl font-bold text-white">
                {seoSubjects.reduce((acc, s) => acc + s.topics.length, 0)}
              </span>
              <span className="ml-2">Topics</span>
            </div>
            <div>
              <span className="text-2xl font-bold text-white">2</span>
              <span className="ml-2">Qualification Levels</span>
            </div>
          </div>
        </section>
        
        {/* IGCSE Section */}
        <section className="px-4 md:px-8 py-12 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl md:text-3xl font-bold">IGCSE Subjects</h2>
                <p className="text-gray-400 mt-1">International General Certificate of Secondary Education</p>
              </div>
              <Link 
                href="/subjects/igcse"
                className="text-blue-400 hover:text-blue-300 text-sm font-medium"
              >
                View All IGCSE →
              </Link>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {igcseSubjects.map(subject => (
                <Link 
                  key={subject.slug}
                  href={`/subjects/igcse/${subject.slug}`}
                  className="group bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-gray-600 transition-all"
                >
                  <h3 className="font-semibold text-lg group-hover:text-blue-400 transition-colors">
                    {subject.name}
                  </h3>
                  <p className="text-sm text-gray-500 mb-3">{subject.examCode}</p>
                  <p className="text-gray-400 text-sm">{subject.shortDescription}</p>
                  <div className="flex gap-3 text-xs text-gray-500 mt-3">
                    <span>{subject.topics.length} topics</span>
                    <span>•</span>
                    <span>{subject.yearsAvailable.length} years</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
        
        {/* A Level Section */}
        <section className="px-4 md:px-8 py-12 max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold">A Level Subjects</h2>
              <p className="text-gray-400 mt-1">International Advanced Level (IAL)</p>
            </div>
            <Link 
              href="/subjects/ial"
              className="text-blue-400 hover:text-blue-300 text-sm font-medium"
            >
              View All A Level →
            </Link>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {ialSubjects.map(subject => (
              <Link 
                key={subject.slug}
                href={`/subjects/ial/${subject.slug}`}
                className="group bg-gray-900 rounded-lg p-5 border border-gray-800 hover:border-gray-600 transition-all"
              >
                <h3 className="font-semibold text-lg group-hover:text-blue-400 transition-colors">
                  {subject.name}
                </h3>
                <p className="text-sm text-gray-500 mb-3">{subject.examCode}</p>
                <p className="text-gray-400 text-sm">{subject.shortDescription}</p>
                <div className="flex gap-3 text-xs text-gray-500 mt-3">
                  <span>{subject.topics.length} topics</span>
                  <span>•</span>
                  <span>{subject.yearsAvailable.length} years</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
        
        {/* CTA Section */}
        <section className="px-4 md:px-8 py-16 bg-gray-950">
          <div className="max-w-6xl mx-auto">
            <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 rounded-2xl p-8 md:p-12 text-center">
              <h2 className="text-2xl md:text-3xl font-bold mb-4">
                Can&apos;t Find Your Subject?
              </h2>
              <p className="text-gray-300 mb-8 max-w-2xl mx-auto">
                We&apos;re constantly adding new subjects. Let us know what you&apos;re studying 
                and we&apos;ll prioritize adding it.
              </p>
              <Link 
                href="/contact"
                className="inline-block bg-white text-gray-900 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
              >
                Request a Subject
              </Link>
            </div>
          </div>
        </section>
      </main>
    </>
  )
}
