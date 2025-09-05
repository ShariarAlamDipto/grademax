import './globals.css'
// ...existing code...
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'




export const metadata = {
  title: 'GradeMax',
  description: 'Empowering Your Studies',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-black text-white">
        <Navbar />
        <div className="pt-20">{children}</div> {/* pushes content below navbar */}
        <Footer />
      </body>
    </html>
  )
}
