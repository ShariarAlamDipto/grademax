import type { Metadata } from 'next'

// Auth page: keep it out of search results. Every protected route funnels here
// (?next=…), so without noindex Google indexes dozens of /login?next=… variants.
export const metadata: Metadata = {
  title: 'Sign In',
  robots: { index: false, follow: false },
  alternates: {
    canonical: 'https://www.grademax.me/login',
  },
}

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
