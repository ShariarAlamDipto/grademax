import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Past Papers',
  description: 'GradeMax Past Papers - Access IGCSE and A Level past examination papers with mark schemes. Download or practice online.',
  keywords: ['GradeMax past papers', 'IGCSE papers', 'A Level papers', 'Cambridge past papers', 'Edexcel past papers', 'exam papers'],
  openGraph: {
    title: 'GradeMax - Past Papers Collection',
    description: 'Access IGCSE and A Level past examination papers with mark schemes.',
    url: 'https://grademax.me/past-papers',
  },
  alternates: {
    canonical: 'https://grademax.me/past-papers',
  },
}

export default function PastPapersLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
