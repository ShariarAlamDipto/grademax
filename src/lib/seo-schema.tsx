/**
 * JSON-LD Schema Generators for SEO
 * Generates structured data for Google rich results
 */

import { SEOSubject, Topic, getLevelDisplay } from './seo-subjects'

const BASE_URL = 'https://grademax.me'
const ORG_ID = `${BASE_URL}/#organization`
const WEBSITE_ID = `${BASE_URL}/#website`

/**
 * Organization schema - use on every page
 */
export function generateOrganizationSchema() {
  return {
    '@type': 'Organization',
    '@id': ORG_ID,
    name: 'GradeMax',
    url: BASE_URL,
    logo: {
      '@type': 'ImageObject',
      url: `${BASE_URL}/logo.png`,
      width: 512,
      height: 512
    },
    description: 'GradeMax provides free Edexcel IGCSE and A Level past papers, topic-wise questions, custom worksheets, and mark schemes.',
    sameAs: [
      // Add social profiles when created
    ]
  }
}

/**
 * WebSite schema - use on homepage
 */
export function generateWebSiteSchema() {
  return {
    '@type': 'WebSite',
    '@id': WEBSITE_ID,
    url: BASE_URL,
    name: 'GradeMax',
    description: 'Free Edexcel IGCSE and A Level Past Papers, Custom Worksheets, and Topic-Wise Questions',
    publisher: { '@id': ORG_ID },
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${BASE_URL}/browse?q={search_term_string}`
      },
      'query-input': 'required name=search_term_string'
    },
    inLanguage: 'en-US'
  }
}

/**
 * Course schema for subject pages
 */
export function generateCourseSchema(subject: SEOSubject) {
  return {
    '@type': 'Course',
    '@id': `${BASE_URL}/subjects/${subject.level}/${subject.slug}#course`,
    name: `${subject.levelDisplay} ${subject.name}`,
    description: subject.longDescription,
    provider: { '@id': ORG_ID },
    educationalLevel: subject.levelDisplay,
    about: subject.topics.map(topic => ({
      '@type': 'DefinedTerm',
      name: topic.name,
      description: topic.description
    })),
    hasCourseInstance: {
      '@type': 'CourseInstance',
      courseMode: 'online',
      courseWorkload: 'PT100H' // Estimated 100 hours
    },
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
      availability: 'https://schema.org/InStock'
    }
  }
}

/**
 * FAQPage schema for subject/topic pages with FAQs
 */
export function generateFAQSchema(faqs: { question: string; answer: string }[]) {
  return {
    '@type': 'FAQPage',
    mainEntity: faqs.map(faq => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer
      }
    }))
  }
}

/**
 * HowTo schema for tutorial/how-to-solve pages
 */
export function generateHowToSchema(
  name: string,
  description: string,
  steps: { name: string; text: string }[],
  totalTime?: string // e.g., "PT10M" for 10 minutes
) {
  return {
    '@type': 'HowTo',
    name,
    description,
    totalTime: totalTime || 'PT15M',
    step: steps.map((step, index) => ({
      '@type': 'HowToStep',
      position: index + 1,
      name: step.name,
      text: step.text
    }))
  }
}

/**
 * BreadcrumbList schema for navigation
 */
export function generateBreadcrumbSchema(
  items: { name: string; url: string }[]
) {
  return {
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url
    }))
  }
}

/**
 * WebPage schema for general pages
 */
export function generateWebPageSchema(
  url: string,
  name: string,
  description: string,
  breadcrumbs?: { name: string; url: string }[]
) {
  const schema: Record<string, unknown> = {
    '@type': 'WebPage',
    '@id': `${url}#webpage`,
    url,
    name,
    description,
    isPartOf: { '@id': WEBSITE_ID },
    about: { '@id': ORG_ID },
    inLanguage: 'en-US'
  }
  
  if (breadcrumbs) {
    schema.breadcrumb = generateBreadcrumbSchema(breadcrumbs)
  }
  
  return schema
}

/**
 * LearningResource schema for educational content
 */
export function generateLearningResourceSchema(
  subject: SEOSubject,
  topic?: Topic
) {
  const name = topic 
    ? `${subject.levelDisplay} ${subject.name} - ${topic.name}`
    : `${subject.levelDisplay} ${subject.name}`
  
  const url = topic
    ? `${BASE_URL}/subjects/${subject.level}/${subject.slug}/${topic.slug}`
    : `${BASE_URL}/subjects/${subject.level}/${subject.slug}`
  
  return {
    '@type': 'LearningResource',
    '@id': `${url}#learningresource`,
    name,
    description: topic?.description || subject.longDescription,
    educationalLevel: subject.levelDisplay,
    learningResourceType: ['Practice Problem', 'Past Paper', 'Quiz'],
    educationalAlignment: {
      '@type': 'AlignmentObject',
      alignmentType: 'educationalSubject',
      targetName: subject.name,
      educationalFramework: subject.examBoard
    },
    provider: { '@id': ORG_ID },
    isAccessibleForFree: true,
    inLanguage: 'en-US'
  }
}

/**
 * ItemList schema for list pages (e.g., list of past papers)
 */
export function generateItemListSchema(
  name: string,
  items: { name: string; url: string; position: number }[]
) {
  return {
    '@type': 'ItemList',
    name,
    numberOfItems: items.length,
    itemListElement: items.map(item => ({
      '@type': 'ListItem',
      position: item.position,
      name: item.name,
      url: item.url
    }))
  }
}

/**
 * Complete schema for subject page
 */
export function generateSubjectPageSchema(subject: SEOSubject) {
  const url = `${BASE_URL}/subjects/${subject.level}/${subject.slug}`
  
  return {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateCourseSchema(subject),
      generateLearningResourceSchema(subject),
      generateFAQSchema(subject.faqs),
      generateBreadcrumbSchema([
        { name: 'Home', url: BASE_URL },
        { name: getLevelDisplay(subject.level), url: `${BASE_URL}/subjects/${subject.level}` },
        { name: subject.name, url }
      ]),
      generateWebPageSchema(
        url,
        subject.metaTitle,
        subject.metaDescription,
        [
          { name: 'Home', url: BASE_URL },
          { name: getLevelDisplay(subject.level), url: `${BASE_URL}/subjects/${subject.level}` },
          { name: subject.name, url }
        ]
      )
    ]
  }
}

/**
 * Complete schema for topic page
 */
export function generateTopicPageSchema(subject: SEOSubject, topic: Topic) {
  const url = `${BASE_URL}/subjects/${subject.level}/${subject.slug}/${topic.slug}`
  
  return {
    '@context': 'https://schema.org',
    '@graph': [
      generateOrganizationSchema(),
      generateLearningResourceSchema(subject, topic),
      generateBreadcrumbSchema([
        { name: 'Home', url: BASE_URL },
        { name: getLevelDisplay(subject.level), url: `${BASE_URL}/subjects/${subject.level}` },
        { name: subject.name, url: `${BASE_URL}/subjects/${subject.level}/${subject.slug}` },
        { name: topic.name, url }
      ]),
      generateWebPageSchema(
        url,
        `${topic.name} - ${subject.levelDisplay} ${subject.name} | GradeMax`,
        topic.description,
        [
          { name: 'Home', url: BASE_URL },
          { name: getLevelDisplay(subject.level), url: `${BASE_URL}/subjects/${subject.level}` },
          { name: subject.name, url: `${BASE_URL}/subjects/${subject.level}/${subject.slug}` },
          { name: topic.name, url }
        ]
      )
    ]
  }
}

/**
 * Schema component wrapper
 */
export function SchemaScript({ schema }: { schema: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
