
import './globals.css'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Analytics } from '@vercel/analytics/react'
import { Playfair_Display } from 'next/font/google'
import { SpeedInsights } from "@vercel/speed-insights/next"
import type { Metadata } from 'next'
import Script from 'next/script'

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['400','500','600','700','800','900'] });

// JSON-LD Structured Data for Brand Recognition
const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      '@id': 'https://grademax.me/#organization',
      name: 'GradeMax',
      url: 'https://grademax.me',
      logo: {
        '@type': 'ImageObject',
        url: 'https://grademax.me/logo.png',
        width: 512,
        height: 512
      },
      description: 'GradeMax is the ultimate AI-powered study platform for IGCSE and A Level students.',
      sameAs: [
        // Add your social profiles here when created
        // 'https://twitter.com/grademax',
        // 'https://facebook.com/grademax',
        // 'https://linkedin.com/company/grademax'
      ]
    },
    {
      '@type': 'WebSite',
      '@id': 'https://grademax.me/#website',
      url: 'https://grademax.me',
      name: 'GradeMax',
      description: 'AI-Powered Study Assistant for IGCSE & A Level Students',
      publisher: {
        '@id': 'https://grademax.me/#organization'
      },
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: 'https://grademax.me/browse?q={search_term_string}'
        },
        'query-input': 'required name=search_term_string'
      },
      inLanguage: 'en-US'
    },
    {
      '@type': 'WebPage',
      '@id': 'https://grademax.me/#webpage',
      url: 'https://grademax.me',
      name: 'GradeMax - AI Study Assistant for IGCSE & A Level Students',
      isPartOf: {
        '@id': 'https://grademax.me/#website'
      },
      about: {
        '@id': 'https://grademax.me/#organization'
      },
      description: 'GradeMax helps IGCSE and A Level students prepare for exams with AI-powered worksheet generation and topic-wise past paper practice.',
      inLanguage: 'en-US'
    },
    {
      '@type': 'EducationalOrganization',
      '@id': 'https://grademax.me/#educationalorg',
      name: 'GradeMax',
      url: 'https://grademax.me',
      description: 'Online study platform providing exam preparation resources for IGCSE and A Level students worldwide.',
      areaServed: 'Worldwide',
      audience: {
        '@type': 'EducationalAudience',
        educationalRole: 'student',
        audienceType: 'IGCSE and A Level students'
      }
    }
  ]
}

export const metadata: Metadata = {
  metadataBase: new URL('https://grademax.me'),
  title: {
    default: 'GradeMax - AI Study Assistant for IGCSE & A Level Students',
    template: '%s | GradeMax'
  },
  description: 'GradeMax is the ultimate AI-powered study platform for IGCSE and A Level students. Generate custom worksheets from past papers, practice topic-wise questions, and ace your exams with smart revision tools.',
  keywords: ['GradeMax', 'grademax', 'grade max', 'IGCSE study', 'A Level revision', 'past papers', 'worksheet generator', 'exam preparation', 'Cambridge IGCSE', 'Edexcel A Level', 'O Level', 'practice questions', 'mark scheme', 'study assistant', 'AI tutor'],
  authors: [{ name: 'GradeMax Team' }],
  creator: 'GradeMax',
  publisher: 'GradeMax',
  applicationName: 'GradeMax',
  generator: 'Next.js',
  referrer: 'origin-when-cross-origin',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  alternates: {
    canonical: 'https://grademax.me',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://grademax.me',
    siteName: 'GradeMax',
    title: 'GradeMax - AI Study Assistant for IGCSE & A Level Students',
    description: 'Generate custom worksheets from past papers, practice topic-wise questions, and ace your IGCSE & A Level exams with GradeMax.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'GradeMax - Smart Exam Preparation for IGCSE & A Level',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'GradeMax - AI Study Assistant for IGCSE & A Level',
    description: 'Generate custom worksheets from past papers and ace your exams with GradeMax.',
    images: ['/og-image.png'],
    creator: '@grademax',
    site: '@grademax',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  category: 'education',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={playfair.className}>
      <head>
        <Script
          id="json-ld"
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <link rel="canonical" href="https://grademax.me" />
      </head>
      <body className="bg-black text-white min-h-screen flex flex-col">
        <Navbar />
        <div className="pt-36 flex-1">{children}</div>
        <Footer />
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
