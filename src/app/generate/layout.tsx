import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Worksheet Generator',
  description: 'GradeMax Worksheet Generator - Create custom IGCSE and A Level practice worksheets from real past papers. Filter by topic, year, and difficulty level.',
  keywords: ['GradeMax worksheet', 'IGCSE worksheet generator', 'A Level practice papers', 'custom worksheets', 'past paper generator', 'exam preparation'],
  openGraph: {
    title: 'GradeMax Worksheet Generator',
    description: 'Create custom IGCSE and A Level practice worksheets from real past papers.',
    url: 'https://grademax.me/generate',
  },
  alternates: {
    canonical: 'https://grademax.me/generate',
  },
}

export default function GenerateLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
