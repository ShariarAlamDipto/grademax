import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Edexcel Past Papers & Mark Schemes – IGCSE & A Level',
  description: 'Download free Edexcel IGCSE and A Level question papers and mark schemes. Browse by subject, year and exam session.',
  keywords: [
    'Edexcel past papers', 'Edexcel past papers free download', 'past papers with mark schemes',
    'IGCSE past papers', 'IGCSE past papers Edexcel', 'Edexcel IGCSE past papers',
    'A Level past papers', 'Edexcel A Level past papers', 'IAL past papers',
    'Edexcel past papers 2025', 'Edexcel past papers 2024', 'Edexcel past papers 2023',
    'IGCSE past papers 2025', 'IGCSE past papers 2024', 'IGCSE past papers 2023',
    'Edexcel Physics past papers', 'Edexcel Maths past papers', 'Edexcel Chemistry past papers',
    'Edexcel Biology past papers', 'Edexcel ICT past papers',
    '4PH1 past papers', '4MA1 past papers', '4MB1 past papers', '4CH1 past papers', '4BI1 past papers',
    'WMA11 past papers', 'WME01 past papers', 'WST01 past papers',
    'Pearson Edexcel past papers', 'Edexcel exam papers', 'Edexcel mark scheme',
    'past papers free', 'IGCSE exam papers', 'A Level exam papers',
    'Edexcel question papers', 'past paper PDF download',
  ],
  openGraph: {
    title: 'Edexcel Past Papers & Mark Schemes – IGCSE & A Level | GradeMax',
    description: 'Free Edexcel IGCSE and A Level past papers with mark schemes. Browse by subject, year and session.',
    url: 'https://www.grademax.me/past-papers',
    siteName: 'GradeMax',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Edexcel Past Papers & Mark Schemes – IGCSE & A Level | GradeMax',
    description: 'Free Edexcel IGCSE and A Level past papers with mark schemes by subject, year and session.',
  },
  alternates: {
    canonical: 'https://www.grademax.me/past-papers',
  },
}

export default function PastPapersLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
