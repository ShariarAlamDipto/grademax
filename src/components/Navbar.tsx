import Link from 'next/link'

export default function Navbar() {
  return (
    <nav className="flex flex-col items-center px-8 py-8 bg-black/70 backdrop-blur-md fixed top-0 left-0 w-full z-50 shadow-lg">
      <div className="text-5xl font-bold tracking-wide mb-4 text-center">GradeMax</div>
  <ul className="flex space-x-24 text-xl font-semibold mt-4">
        <li>
          <Link href="/" className="gradient-hover-sea">Home</Link>
        </li>
        <li>
          <Link href="/past-papers" className="gradient-hover-sea">Past Papers</Link>
        </li>
        <li>
          <Link href="/lectures" className="gradient-hover-sea">Lectures</Link>
        </li>
        <li>
          <Link href="/worksheets" className="gradient-hover-sea">Worksheets</Link>
        </li>
      </ul>
    </nav>
  )
}
