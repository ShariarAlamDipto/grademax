import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Test Builder — GradeMax',
  description: 'Build custom test papers by selecting individual questions from past papers. Filter by topic, difficulty, and year. Generate print-ready PDFs with mark schemes.',
  keywords: ['GradeMax test builder', 'custom test paper', 'IGCSE test generator', 'A Level test builder', 'past paper questions', 'exam preparation'],
  openGraph: {
    title: 'GradeMax Test Builder',
    description: 'Build custom test papers from real past paper questions.',
    url: 'https://grademax.me/test-builder',
  },
  alternates: {
    canonical: 'https://grademax.me/test-builder',
  },
}

export default function TestBuilderLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
