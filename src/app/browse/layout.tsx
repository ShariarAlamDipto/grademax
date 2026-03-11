import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Browse Edexcel Past Paper Questions by Topic – IGCSE & A Level',
  description: 'Browse Edexcel IGCSE and A Level past paper questions organized by topic. Practice topic-wise questions for Physics, Maths, Chemistry, Biology with mark schemes. Free and no sign-up required.',
  keywords: [
    'Edexcel questions by topic', 'topic wise past papers', 'IGCSE questions by topic',
    'A Level questions by topic', 'past paper questions by topic', 'Edexcel topic browser',
    'IGCSE Physics questions', 'IGCSE Maths questions', 'IGCSE Chemistry questions',
    'topic wise questions with mark schemes', 'chapterwise questions Edexcel',
    'Edexcel past papers by chapter', 'exam practice by topic',
  ],
  openGraph: {
    title: 'Browse Edexcel Past Paper Questions by Topic | GradeMax',
    description: 'Practice Edexcel IGCSE and A Level questions organized by topic with mark schemes.',
    url: 'https://grademax.me/browse',
    siteName: 'GradeMax',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Edexcel Questions by Topic | GradeMax',
    description: 'Browse past paper questions by topic with mark schemes.',
  },
  alternates: {
    canonical: 'https://grademax.me/browse',
  },
}

export default function BrowseLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
