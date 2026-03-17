import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Free Edexcel Past Papers 2025 – IGCSE & A Level with Mark Schemes | GradeMax',
  description: 'Download free Edexcel IGCSE and A Level past papers with mark schemes (2011–2025). Browse Physics, Maths, Chemistry, Biology, ICT and more – all question papers organised by year and session.',
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
    title: 'Free Edexcel Past Papers 2025 – IGCSE & A Level | GradeMax',
    description: 'Free Edexcel IGCSE and A Level past papers with mark schemes. Physics, Maths, Chemistry, Biology, ICT – all sessions 2011–2025.',
    url: 'https://grademax.me/past-papers',
    siteName: 'GradeMax',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Free Edexcel Past Papers 2025 – IGCSE & A Level | GradeMax',
    description: 'Free Edexcel IGCSE and A Level past papers with mark schemes (2011–2025).',
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
