import type { Metadata } from 'next'

// Root template appends "| GradeMax" — no manual brand in the title.
export const metadata: Metadata = {
  title: 'Edexcel Test Builder – Create Custom Test Papers Free',
  description: 'Build custom Edexcel IGCSE test papers question by question. Pick topics, difficulty and years from real past papers — Physics, Maths, Chemistry, Biology — and download print-ready PDFs with mark schemes.',
  keywords: [
    'test builder', 'Edexcel test builder', 'custom test paper generator',
    'IGCSE test generator', 'create test from past papers', 'mock exam builder',
    'custom exam paper maker', 'past paper question picker', 'test maker for students',
    'IGCSE Physics test builder', 'IGCSE Maths test builder', 'IGCSE Chemistry test builder',
    'IGCSE Biology test builder', 'build your own exam paper', 'exam preparation',
  ],
  openGraph: {
    title: 'Edexcel Test Builder – Create Custom Test Papers Free | GradeMax',
    description: 'Build custom test papers from real Edexcel past paper questions with mark schemes.',
    url: 'https://www.grademax.me/test-builder',
    siteName: 'GradeMax',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Edexcel Test Builder – Create Custom Test Papers Free | GradeMax',
    description: 'Build custom test papers from real Edexcel past paper questions with mark schemes.',
  },
  alternates: {
    canonical: 'https://www.grademax.me/test-builder',
  },
}

export default function TestBuilderLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
