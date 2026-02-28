import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Browse Questions by Topic',
  description: 'GradeMax Topic Browser - Browse IGCSE and A Level past paper questions organized by topic. Find practice questions with mark schemes included.',
  keywords: ['GradeMax topics', 'IGCSE questions by topic', 'A Level past papers', 'topic-wise questions', 'exam practice', 'mark schemes'],
  openGraph: {
    title: 'GradeMax - Browse Questions by Topic',
    description: 'Browse IGCSE and A Level past paper questions organized by topic.',
    url: 'https://grademax.me/browse',
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
