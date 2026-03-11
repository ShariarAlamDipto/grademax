import { MetadataRoute } from 'next'
import { seoSubjects, type SEOSubject } from '@/lib/seo-subjects'
import { pastPaperSubjects } from '@/lib/subjects'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://grademax.me'
  const now = new Date()
  
  // Core pages
  const corePages: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${baseUrl}/edexcel-past-papers`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.95,
    },
    {
      url: `${baseUrl}/edexcel-igcse-past-papers`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.95,
    },
    {
      url: `${baseUrl}/edexcel-a-level-past-papers`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.95,
    },
    {
      url: `${baseUrl}/edexcel-worksheets`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.95,
    },
    {
      url: `${baseUrl}/subjects`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/generate`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/browse`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/past-papers`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${baseUrl}/contact`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: now,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: now,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ]
  
  // Level landing pages
  const levelPages: MetadataRoute.Sitemap = [
    {
      url: `${baseUrl}/subjects/igcse`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/subjects/ial`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
  ]
  
  // Subject pages (pillar pages)
  const subjectPages: MetadataRoute.Sitemap = seoSubjects.map((subject: SEOSubject) => ({
    url: `${baseUrl}/subjects/${subject.level}/${subject.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))
  
  // Topic pages (supporting pages)
  const topicPages: MetadataRoute.Sitemap = seoSubjects.flatMap((subject: SEOSubject) =>
    subject.topics.map(topic => ({
      url: `${baseUrl}/subjects/${subject.level}/${subject.slug}/${topic.slug}`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: 0.75,
    }))
  )
  
  // Past paper subject pages (actual route: /past-papers/{slug})
  const pastPaperSubjectPages: MetadataRoute.Sitemap = pastPaperSubjects.map((subject) => ({
    url: `${baseUrl}/past-papers/${subject.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.8,
  }))
  
  // SEO subject past paper pages (subject-level detail)
  const seoPastPaperPages: MetadataRoute.Sitemap = seoSubjects.map((subject: SEOSubject) => ({
    url: `${baseUrl}/past-papers/${subject.level}/${subject.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }))
  
  // Past papers by year (for subjects with years available)
  const pastPaperYearPages: MetadataRoute.Sitemap = seoSubjects.flatMap((subject: SEOSubject) =>
    subject.yearsAvailable.map(year => ({
      url: `${baseUrl}/past-papers/${subject.level}/${subject.slug}/${year}`,
      lastModified: now,
      changeFrequency: 'yearly' as const,
      priority: 0.6,
    }))
  )
  
  // QP landing pages — high-intent keyword pages for each subject
  // These target queries like "edexcel igcse physics past papers", "4PH1 past papers", etc.
  const qpPages: MetadataRoute.Sitemap = seoSubjects.flatMap((subject: SEOSubject) => {
    const levelPrefix = subject.level === 'igcse' ? 'igcse' : 'a-level'
    return [
      // Primary: /qp/igcse-physics
      {
        url: `${baseUrl}/qp/${levelPrefix}-${subject.slug}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.9,
      },
      // With "past-papers": /qp/igcse-physics-past-papers
      {
        url: `${baseUrl}/qp/${levelPrefix}-${subject.slug}-past-papers`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.9,
      },
      // With "question-papers": /qp/igcse-physics-question-papers
      {
        url: `${baseUrl}/qp/${levelPrefix}-${subject.slug}-question-papers`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.85,
      },
      // Exam code: /qp/4ph1
      {
        url: `${baseUrl}/qp/${subject.examCode.toLowerCase()}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.85,
      },
      // Exam code with past papers: /qp/4ph1-past-papers
      {
        url: `${baseUrl}/qp/${subject.examCode.toLowerCase()}-past-papers`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.85,
      },
    ]
  })
  
  return [
    ...corePages,
    ...levelPages,
    ...subjectPages,
    ...topicPages,
    ...pastPaperSubjectPages,
    ...seoPastPaperPages,
    ...pastPaperYearPages,
    ...qpPages,
  ]
}
