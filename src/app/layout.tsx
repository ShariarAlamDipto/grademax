
import './globals.css'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Analytics } from '@vercel/analytics/react'   // ✅ import Analytics
import { Playfair_Display } from 'next/font/google'
import { SpeedInsights } from "@vercel/speed-insights/next"

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['400','500','600','700','800','900'] });

export const metadata = {
  title: 'GradeMax',
  description: 'Empowering Your Studies',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={playfair.className}>
      <body className="bg-black text-white min-h-screen flex flex-col">
        <Navbar />
  <div className="pt-36 flex-1">{children}</div> {/* pushes content below navbar */}
        <Footer />
        <Analytics />   {/* ✅ add Analytics here */}
        <SpeedInsights/> {/* Add Speed Insights component */}
      </body>
    </html>
  )
}
