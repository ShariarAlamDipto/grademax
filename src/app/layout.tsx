
import './globals.css'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Analytics } from '@vercel/analytics/react'
import { Playfair_Display } from 'next/font/google'
import { SpeedInsights } from "@vercel/speed-insights/next"
import type { Metadata } from 'next'
import { AuthProvider } from '@/context/AuthContext'

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['600','700'], display: 'swap' });

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
        url: 'https://grademax.me/icon.svg',
        width: 512,
        height: 512
      },
      description: 'GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, and ace your Cambridge and Edexcel exams with smart revision tools.',
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
      name: 'GradeMax - Past Papers | Chapterwise Worksheet | Lecture Notes',
      isPartOf: {
        '@id': 'https://grademax.me/#website'
      },
      about: {
        '@id': 'https://grademax.me/#organization'
      },
      description: 'GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, and ace your Cambridge and Edexcel exams with smart revision tools.',
      inLanguage: 'en-US'
    },
    {
      '@type': 'EducationalOrganization',
      '@id': 'https://grademax.me/#educationalorg',
      name: 'GradeMax',
      url: 'https://grademax.me',
      description: 'GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, and ace your Cambridge and Edexcel exams with smart revision tools.',
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
    default: 'GradeMax - Past Papers | Chapterwise Worksheet | Lecture Notes',
    template: '%s | GradeMax'
  },
  description: 'GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, and ace your Cambridge and Edexcel exams with smart revision tools.',
  keywords: ['GradeMax', 'grademax', 'grade max', 'IGCSE study', 'A Level revision', 'past papers', 'worksheet generator', 'exam preparation', 'Cambridge IGCSE', 'Edexcel A Level', 'O Level', 'practice questions', 'mark scheme', 'study assistant', 'AI tutor'],
  authors: [{ name: 'GradeMax Team' }],
  creator: 'GradeMax',
  publisher: 'GradeMax',
  applicationName: 'GradeMax',
  icons: {
    icon: '/icon.svg',
    apple: '/apple-icon.png',
  },
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
    title: 'GradeMax - Past Papers | Chapterwise Worksheet | Lecture Notes',
    description: 'GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, and ace your Cambridge and Edexcel exams with smart revision tools.',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'GradeMax - Study Assistant for IGCSE & A Level Success',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'GradeMax - Study Assistant for IGCSE & A Level Success',
    description: 'GradeMax helps you generate custom worksheets from real past papers, practice topic-wise questions, and ace your Cambridge and Edexcel exams.',
    images: ['/opengraph-image'],
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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="bg-black text-white min-h-screen flex flex-col">
        <AuthProvider>
          <Navbar />
          <div className="pt-36 flex-1">{children}</div>
          <Footer />
        </AuthProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
