
import './globals.css'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Analytics } from '@vercel/analytics/react'
import { Playfair_Display } from 'next/font/google'
import { SpeedInsights } from "@vercel/speed-insights/next"
import type { Metadata } from 'next'

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['400','500','600','700','800','900'] });

export const metadata: Metadata = {
  metadataBase: new URL('https://grademax.me'),
  title: {
    default: 'GradeMax - AI Study Assistant for IGCSE & A Level Students',
    template: '%s | GradeMax'
  },
  description: 'GradeMax is the ultimate AI-powered study platform for IGCSE and A Level students. Generate custom worksheets from past papers, practice topic-wise questions, and ace your exams with smart revision tools.',
  keywords: ['IGCSE', 'A Level', 'past papers', 'study assistant', 'worksheet generator', 'exam preparation', 'Cambridge', 'Edexcel', 'O Level', 'revision', 'practice questions', 'mark scheme'],
  authors: [{ name: 'GradeMax Team' }],
  creator: 'GradeMax',
  publisher: 'GradeMax',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://grademax.me',
    siteName: 'GradeMax',
    title: 'GradeMax - AI Study Assistant for IGCSE & A Level Students',
    description: 'Generate custom worksheets from past papers, practice topic-wise questions, and ace your IGCSE & A Level exams.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'GradeMax - Smart Exam Preparation',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'GradeMax - AI Study Assistant for IGCSE & A Level',
    description: 'Generate custom worksheets from past papers and ace your exams.',
    images: ['/og-image.png'],
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
  verification: {
    google: 'your-google-verification-code', // Add your Google Search Console verification code
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={playfair.className}>
      <body className="bg-black text-white min-h-screen flex flex-col">
        <Navbar />
  <div className="pt-36 flex-1">{children}</div> {/* pushes content below navbar */}
        <Footer />
        <Analytics />   {/* ✅ add Analytics here */}
        <SpeedInsights/> {/* Add Speed Insights component */}
      </body>
    </html>
  )
}
