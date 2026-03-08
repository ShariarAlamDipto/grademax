import { MetadataRoute } from 'next'
import { seoSubjects, type SEOSubject } from '@/lib/seo-subjects'

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
  
  // Past papers by subject
  const pastPaperSubjectPages: MetadataRoute.Sitemap = seoSubjects.map((subject: SEOSubject) => ({
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
  
  // Practice pages
  const practicePages: MetadataRoute.Sitemap = seoSubjects.map((subject: SEOSubject) => ({
    url: `${baseUrl}/practice/${subject.level}/${subject.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }))
  
  // Worksheets pages
  const worksheetPages: MetadataRoute.Sitemap = seoSubjects.map((subject: SEOSubject) => ({
    url: `${baseUrl}/worksheets/${subject.level}/${subject.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }))
  
  return [
    ...corePages,
    ...levelPages,
    ...subjectPages,
    ...topicPages,
    ...pastPaperSubjectPages,
    ...pastPaperYearPages,
    ...practicePages,
    ...worksheetPages,
  ]
}
