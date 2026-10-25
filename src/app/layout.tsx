
import './globals.css'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Analytics } from '@vercel/analytics/next'
import { SpeedInsights } from '@vercel/speed-insights/next'
import VisitTracker from '@/components/VisitTracker'
import { Playfair_Display } from 'next/font/google'
import type { Metadata } from 'next'
import { AuthProvider } from '@/context/AuthContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { ADSENSE_SCRIPT_SRC } from '@/lib/ads'
import { SOCIAL_SAME_AS } from '@/lib/social'

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['600','700','800'], display: 'swap' });

// Evaluated at build time; every deploy refreshes it, so titles never advertise a
// stale year (the hardcoded "2025" sat live well into 2026).
const CURRENT_YEAR = new Date().getFullYear()

// JSON-LD Structured Data for Brand Recognition & Edexcel SEO
const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      '@id': 'https://www.grademax.me/#organization',
      name: 'GradeMax',
      url: 'https://www.grademax.me',
      logo: {
        '@type': 'ImageObject',
        url: 'https://www.grademax.me/logo.png',
        width: 512,
        height: 512
      },
      description: 'Free Edexcel past papers, topic-wise question papers, and custom worksheet generator for IGCSE and A Level students. Access mark schemes, practice papers, and revision resources for Physics, Maths, Chemistry, Biology, ICT and more.',
      foundingDate: '2024',
      knowsAbout: ['Edexcel past papers', 'IGCSE', 'A Level', 'Pearson Edexcel', 'Past paper questions', 'Mark schemes'],
      // Only real, GradeMax-controlled profiles (see src/lib/social.tsx).
      sameAs: SOCIAL_SAME_AS,
    },
    {
      '@type': 'WebSite',
      '@id': 'https://www.grademax.me/#website',
      url: 'https://www.grademax.me',
      name: 'GradeMax',
      description: `Free Edexcel IGCSE and A Level Past Papers ${CURRENT_YEAR}, Custom Worksheets and Topic-Wise Questions with Mark Schemes`,
      publisher: {
        '@id': 'https://www.grademax.me/#organization'
      },
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: 'https://www.grademax.me/browse?q={search_term_string}'
        },
        'query-input': 'required name=search_term_string'
      },
      inLanguage: 'en-GB'
    },
    {
      '@type': 'EducationalOrganization',
      '@id': 'https://www.grademax.me/#educationalorg',
      name: 'GradeMax',
      url: 'https://www.grademax.me',
      description: 'Free online platform for Edexcel IGCSE and A Level exam preparation with past papers, custom worksheets, and topic-wise practice questions.',
      areaServed: 'Worldwide',
      audience: {
        '@type': 'EducationalAudience',
        educationalRole: 'student',
        audienceType: 'Edexcel IGCSE and A Level students worldwide'
      }
    },
  ]
}

export const metadata: Metadata = {
  metadataBase: new URL('https://www.grademax.me'),
  title: {
    default: `Edexcel Past Papers ${CURRENT_YEAR} – Free IGCSE & A Level | GradeMax`,
    template: '%s | GradeMax'
  },
  description: 'Free Edexcel and Cambridge IGCSE and A Level past papers with mark schemes. Browse by subject, year and session, or build Edexcel practice worksheets.',
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
      { url: '/favicon.ico',  sizes: '48x48',   type: 'image/x-icon' },
      { url: '/icon-32.png',  sizes: '32x32',   type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/favicon.png',  sizes: '512x512', type: 'image/png' },
    ],
    shortcut: '/favicon.png',
    apple: [
      { url: '/favicon.png', sizes: '512x512', type: 'image/png' },
    ],
  },
  referrer: 'origin-when-cross-origin',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: 'website',
    locale: 'en_GB',
    siteName: 'GradeMax',
    title: `Edexcel Past Papers ${CURRENT_YEAR} | Free IGCSE & A Level | GradeMax`,
    description: 'Free Edexcel and Cambridge past papers with mark schemes for IGCSE and A Level. Find papers by subject, year and session, and create Edexcel worksheets.',
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
    title: `Edexcel Past Papers ${CURRENT_YEAR} | Free IGCSE & A Level Questions | GradeMax`,
    description: 'Free Edexcel and Cambridge IGCSE and A Level past papers with mark schemes, plus custom Edexcel worksheets and topic-wise practice.',
    images: ['/opengraph-image'],
    // creator/site omitted — re-add only if the @grademax handle is actually owned.
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
    <html lang="en-GB" className={playfair.className} suppressHydrationWarning>
      <head>
        {/* next/font self-hosts Playfair Display — no runtime request to Google
            Fonts, so no preconnect needed (removed: it opened a dead TLS
            connection on every visit). */}
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
        {/* AdSense loader. It sits in the root layout's <head> deliberately:
            AdSense's site review requires the snippet in the server-rendered
            HTML of every page, so next/script (which injects it client-side,
            into the body) would not satisfy it. async, so it never blocks the
            first paint. */}
        <script async src={ADSENSE_SCRIPT_SRC} crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen flex flex-col" style={{ background: 'var(--gm-bg)', color: 'var(--gm-text)' }}>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded focus:text-sm">Skip to content</a>
        <ThemeProvider>
          <AuthProvider>
            <Navbar />
            <div id="main-content" className="pt-[var(--gm-nav-h)] flex-1">
              {children}
            </div>
            <Footer />
          </AuthProvider>
        </ThemeProvider>
        <Analytics />
        <SpeedInsights />
        <VisitTracker />
      </body>
    </html>
  )
}
