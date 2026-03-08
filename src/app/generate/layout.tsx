import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Edexcel Worksheet Generator – Create Custom Past Paper Worksheets Free',
  description: 'Free Edexcel worksheet generator. Create custom IGCSE and A Level practice worksheets from real past paper questions. Filter by topic, year, and difficulty. Download PDF with mark schemes.',
  keywords: [
    'worksheet generator', 'Edexcel worksheet generator', 'custom worksheet generator',
    'IGCSE worksheet generator', 'A Level worksheet generator',
    'past paper generator', 'practice paper generator',
    'Edexcel worksheets', 'custom worksheets', 'exam worksheets',
    'maths worksheet generator', 'physics worksheet generator',
    'create worksheets from past papers', 'download worksheets free',
  ],
  openGraph: {
    title: 'Edexcel Worksheet Generator – Create Custom Past Paper Worksheets Free',
    description: 'Create custom Edexcel IGCSE and A Level practice worksheets from real past papers. Free with mark schemes.',
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
