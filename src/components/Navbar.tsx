import Link from 'next/link'

export default function Navbar() {
  return (
    <nav className="flex justify-between items-center px-8 py-4 bg-black/70 backdrop-blur-md fixed top-0 left-0 w-full z-50">
      <div className="text-2xl font-light tracking-wide">GradeMax</div>
      <ul className="flex space-x-8 text-lg">
        <li><Link href="/past-papers">Past Papers</Link></li>
        <li><Link href="/lectures">Lectures</Link></li>
        <li><Link href="/worksheets">Worksheets</Link></li>
      </ul>
    </nav>
  )
}
