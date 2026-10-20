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
    'IGCSE Accounting worksheets', 'IGCSE Business Studies worksheets', 'IGCSE Economics worksheets',
    'IGCSE Computer Science worksheets',
    'create worksheets from past papers', 'download worksheets free',
  ],
  openGraph: {
    title: 'Edexcel Worksheet Generator – Create Custom Past Paper Worksheets Free',
    description: 'Create custom Edexcel IGCSE and A Level practice worksheets from real past papers. Free with mark schemes.',
    url: 'https://www.grademax.me/generate',
  },
  alternates: {
    canonical: 'https://www.grademax.me/generate',
  },
}

const toolSchema = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  '@id': 'https://www.grademax.me/#webapp',
  name: 'GradeMax Worksheet Generator',
  url: 'https://www.grademax.me/generate',
  applicationCategory: 'EducationalApplication',
  operatingSystem: 'Any',
  offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
  description: 'Free custom worksheet generator for Edexcel IGCSE and A Level past paper questions. Select topics, difficulty, and year range to generate a PDF worksheet with mark scheme.',
}

export default function GenerateLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(toolSchema) }} />
      {children}
    </>
  )
}
