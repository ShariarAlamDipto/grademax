
import './globals.css'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Analytics } from '@vercel/analytics/react'
import { Playfair_Display } from 'next/font/google'
import { SpeedInsights } from "@vercel/speed-insights/next"
import type { Metadata } from 'next'
import { AuthProvider } from '@/context/AuthContext'
import { ThemeProvider } from '@/context/ThemeContext'

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['600','700'], display: 'swap' });

// JSON-LD Structured Data for Brand Recognition & Edexcel SEO
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
      description: 'Free Edexcel past papers, topic-wise question papers, and custom worksheet generator for IGCSE and A Level students. Access mark schemes, practice papers, and revision resources for Physics, Maths, Chemistry, Biology, ICT and more.',
      foundingDate: '2024',
      knowsAbout: ['Edexcel past papers', 'IGCSE', 'A Level', 'Pearson Edexcel', 'Past paper questions', 'Mark schemes']
    },
    {
      '@type': 'WebSite',
      '@id': 'https://grademax.me/#website',
      url: 'https://grademax.me',
      name: 'GradeMax',
      description: 'Free Edexcel IGCSE and A Level Past Papers 2025, Custom Worksheets and Topic-Wise Questions with Mark Schemes',
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
      name: 'Edexcel Past Papers 2025 – Free IGCSE & A Level | GradeMax',
      datePublished: '2024-01-15T00:00:00+00:00',
      dateModified: new Date().toISOString(),
      isPartOf: {
        '@id': 'https://grademax.me/#website'
      },
      about: {
        '@id': 'https://grademax.me/#organization'
      },
      description: 'Free Edexcel past papers with mark schemes for IGCSE and A Level (2010-2025). Generate custom worksheets, practice topic-wise questions, and revise with 14+ years of real Pearson Edexcel exam papers.',
      inLanguage: 'en-US',
      speakable: {
        '@type': 'SpeakableSpecification',
        cssSelector: ['h1', '.hero-description']
      }
    },
    {
      '@type': 'EducationalOrganization',
      '@id': 'https://grademax.me/#educationalorg',
      name: 'GradeMax',
      url: 'https://grademax.me',
      description: 'Free online platform for Edexcel IGCSE and A Level exam preparation with past papers, custom worksheets, and topic-wise practice questions.',
      areaServed: 'Worldwide',
      audience: {
        '@type': 'EducationalAudience',
        educationalRole: 'student',
        audienceType: 'Edexcel IGCSE and A Level students worldwide'
      }
    },
    // FAQ Schema for homepage rich snippets
    {
      '@type': 'FAQPage',
      '@id': 'https://grademax.me/#faq',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'Where can I find free Edexcel IGCSE past papers?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'GradeMax offers free Edexcel IGCSE past papers for Physics (4PH1), Maths A (4MA1), Maths B (4MB1), Chemistry (4CH1), Biology (4BI1), and ICT (4IT1). All papers include mark schemes and are organized by topic and year from 2010-2025.'
          }
        },
        {
          '@type': 'Question',
          name: 'How do I generate a custom Edexcel worksheet?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Use the GradeMax Worksheet Generator to create custom worksheets from real Edexcel past paper questions. Select your subject, choose topics, set difficulty levels, pick year ranges, and generate a PDF worksheet with its mark scheme in seconds.'
          }
        },
        {
          '@type': 'Question',
          name: 'What Edexcel A Level past papers are available?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'GradeMax provides Edexcel IAL past papers for Pure Mathematics 1 (WMA11), Mechanics 1 (WME01), and Statistics 1 (WST01), with more units being added. Papers span from 2012-2025 with full mark schemes.'
          }
        },
        {
          '@type': 'Question',
          name: 'Can I practice Edexcel past papers by topic?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Yes! GradeMax organizes all Edexcel past paper questions by topic (chapter-wise). Browse questions for specific topics like Electricity, Algebra, Differentiation, or Organic Chemistry and practice with instant access to mark schemes.'
          }
        },
        {
          '@type': 'Question',
          name: 'Is GradeMax free to use?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Yes, GradeMax is completely free. Access all Edexcel IGCSE and A Level past papers, generate unlimited custom worksheets, and practice topic-wise questions at no cost.'
          }
        }
      ]
    },
    // ItemList for subjects
    {
      '@type': 'ItemList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'IGCSE Physics Past Papers', url: 'https://grademax.me/subjects/igcse/physics' },
        { '@type': 'ListItem', position: 2, name: 'IGCSE Maths A Past Papers', url: 'https://grademax.me/subjects/igcse/maths-a' },
        { '@type': 'ListItem', position: 3, name: 'IGCSE Maths B Past Papers', url: 'https://grademax.me/subjects/igcse/maths-b' },
        { '@type': 'ListItem', position: 4, name: 'IGCSE Chemistry Past Papers', url: 'https://grademax.me/subjects/igcse/chemistry' },
        { '@type': 'ListItem', position: 5, name: 'IGCSE Biology Past Papers', url: 'https://grademax.me/subjects/igcse/biology' },
        { '@type': 'ListItem', position: 6, name: 'IGCSE ICT Past Papers', url: 'https://grademax.me/subjects/igcse/ict' },
        { '@type': 'ListItem', position: 7, name: 'A Level Pure Maths 1 Past Papers', url: 'https://grademax.me/subjects/ial/pure-maths-1' },
        { '@type': 'ListItem', position: 8, name: 'A Level Mechanics 1 Past Papers', url: 'https://grademax.me/subjects/ial/mechanics-1' },
        { '@type': 'ListItem', position: 9, name: 'A Level Statistics 1 Past Papers', url: 'https://grademax.me/subjects/ial/statistics-1' },
      ]
    }
  ]
}

export const metadata: Metadata = {
  metadataBase: new URL('https://grademax.me'),
  title: {
    default: 'Edexcel Past Papers 2025 – Free IGCSE & A Level | GradeMax',
    template: '%s | GradeMax'
  },
  description: 'Free Edexcel IGCSE & A Level past papers with mark schemes (2010–2025). Generate custom worksheets from real Pearson exam questions. Topic-wise practice for Physics, Maths, Chemistry & more.',
  keywords: [
    // Brand
    'GradeMax', 'grademax', 'grade max',
    // Core - Past Papers
    'Edexcel past papers', 'Edexcel past papers with answers', 'Edexcel past papers free',
    'past papers Edexcel', 'past papers with mark schemes',
    'Pearson Edexcel past papers', 'Edexcel exam papers',
    // IGCSE Past Papers
    'IGCSE past papers', 'IGCSE past papers Edexcel', 'Edexcel IGCSE past papers',
    'IGCSE past papers with mark scheme', 'IGCSE past papers free download',
    'international GCSE past papers', 'IGCSE revision papers',
    // IGCSE Subject-Specific
    'IGCSE Physics past papers', 'Edexcel IGCSE Physics past papers', '4PH1 past papers',
    'IGCSE Maths past papers', 'Edexcel IGCSE Maths past papers', '4MA1 past papers', '4MB1 past papers',
    'IGCSE Chemistry past papers', 'Edexcel IGCSE Chemistry past papers', '4CH1 past papers',
    'IGCSE Biology past papers', 'Edexcel IGCSE Biology past papers', '4BI1 past papers',
    'IGCSE ICT past papers', '4IT1 past papers',
    // A Level Past Papers
    'A Level past papers', 'A Level past papers Edexcel', 'Edexcel A Level past papers',
    'IAL past papers', 'International A Level past papers',
    'A Level Maths past papers', 'A Level Maths past papers Edexcel',
    'A Level Physics past papers', 'A Level Chemistry past papers',
    'Pure Maths 1 past papers', 'WMA11 past papers',
    'Mechanics 1 past papers', 'WME01 past papers',
    'Statistics 1 past papers', 'WST01 past papers',
    // Topic-Wise / Chapter-Wise
    'topic wise past papers', 'topic wise questions', 'topicwise past papers',
    'chapter wise past papers', 'chapterwise questions', 'chapterwise past papers',
    'topic wise questions Edexcel', 'Edexcel topic wise past papers',
    'IGCSE topic wise past papers', 'A Level topic wise questions',
    'past papers by topic', 'questions by topic', 'Edexcel questions by topic',
    // Worksheets
    'worksheet generator', 'custom worksheet generator', 'Edexcel worksheet generator',
    'custom worksheets', 'Edexcel worksheets', 'past paper worksheets',
    'create worksheets from past papers', 'exam worksheet generator',
    'IGCSE worksheets', 'A Level worksheets', 'practice worksheets',
    'maths worksheet generator', 'physics worksheet generator',
    // Mark Schemes
    'mark scheme', 'mark schemes Edexcel', 'IGCSE mark scheme',
    'A Level mark scheme', 'past papers with mark scheme',
    'Edexcel marking scheme', 'answer key Edexcel',
    // Year-Specific (high search volume)
    'Edexcel past papers 2025', 'Edexcel past papers 2024', 'Edexcel past papers 2023',
    'IGCSE past papers 2025', 'IGCSE past papers 2024', 'IGCSE past papers 2023',
    'A Level past papers 2025', 'A Level past papers 2024', 'A Level past papers 2023',
    // Revision & Practice
    'IGCSE revision', 'A Level revision', 'Edexcel revision',
    'IGCSE practice questions', 'A Level practice papers',
    'exam preparation', 'exam practice', 'revision resources',
    'study resources Edexcel', 'free exam papers',
    // Question Papers
    'Edexcel question papers', 'IGCSE question papers', 'A Level question papers',
    'topic wise question papers', 'question papers with answers',
  ],
  authors: [{ name: 'GradeMax Team' }],
  creator: 'GradeMax',
  publisher: 'GradeMax',
  applicationName: 'GradeMax',
  icons: {
    icon: [
      { url: '/icon-32.png', sizes: '32x32',  type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon.svg',    type: 'image/svg+xml' },
    ],
    shortcut: '/icon-32.png',
    apple: [
      { url: '/logo.png', sizes: '512x512', type: 'image/png' },
    ],
  },
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
    title: 'Edexcel Past Papers 2025 | Free IGCSE & A Level Topic-Wise Questions with Mark Schemes',
    description: 'Free Edexcel IGCSE and A Level past papers with mark schemes. Generate custom worksheets from real Pearson Edexcel exam questions. Topic-wise practice for Physics, Maths, Chemistry, Biology, ICT and more.',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'GradeMax - Free Edexcel Past Papers & Custom Worksheet Generator',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Edexcel Past Papers 2025 | Free IGCSE & A Level Questions | GradeMax',
    description: 'Free Edexcel IGCSE and A Level past papers with mark schemes (2010-2025). Generate custom worksheets, practice topic-wise, and ace your exams.',
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
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://fonts.gstatic.com" />
        {/* Theme init — runs before paint to prevent flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');document.documentElement.classList.add(t==='light'?'light':'dark');}catch(e){document.documentElement.classList.add('dark');}})();`,
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-screen flex flex-col" style={{ background: 'var(--gm-bg)', color: 'var(--gm-text)' }}>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded focus:text-sm">Skip to content</a>
        <ThemeProvider>
          <AuthProvider>
            <Navbar />
            <div id="main-content" className="pt-[112px] sm:pt-[68px] flex-1">{children}</div>
            <Footer />
          </AuthProvider>
        </ThemeProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
