import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Edexcel Past Papers – Browse IGCSE & A Level by Subject',
  description: 'Browse free Edexcel past papers for IGCSE and A Level subjects including Physics, Mathematics, Chemistry, Biology, and ICT. All papers include mark schemes organized by topic and year.',
  keywords: [
    'Edexcel past papers', 'past papers', 'IGCSE past papers', 'A Level past papers',
    'Edexcel exam papers', 'past papers with mark schemes', 'browse past papers',
    'Edexcel IGCSE past papers', 'Edexcel A Level past papers', 'Pearson Edexcel papers',
    'past papers free download', 'exam papers with answers',
  ],
  openGraph: {
    title: 'Edexcel Past Papers – Browse IGCSE & A Level by Subject',
    description: 'Browse free Edexcel IGCSE and A Level past papers with mark schemes for all subjects.',
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
