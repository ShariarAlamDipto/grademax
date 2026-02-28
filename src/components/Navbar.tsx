"use client";
import Link from 'next/link'
import { useEffect, useState } from 'react'
import AuthButton from './AuthButton'

export default function Navbar() {
  const [isClient, setIsClient] = useState(false)
  useEffect(() => { setIsClient(true) }, [])

  return (
    <nav className="flex flex-col md:flex-row items-center justify-between px-4 md:px-6 py-4 md:py-5 bg-black/70 backdrop-blur-md fixed top-0 left-0 w-full z-50 shadow-lg">
      <div className="text-2xl md:text-4xl font-bold tracking-wide mb-3 md:mb-0 text-center w-full md:w-auto">
        <Link href="/">GradeMax</Link>
      </div>
      <ul className="flex flex-wrap gap-3 md:gap-10 text-sm md:text-xl font-semibold items-center justify-center w-full md:w-auto">
        <li><Link href="/" className="gradient-hover-sea">Home</Link></li>
        <li><Link href="/subjects" className="gradient-hover-sea">Subjects</Link></li>
        <li><Link href="/dashboard" className="gradient-hover-sea">Dashboard</Link></li>
        <li><Link href="/past-papers" className="gradient-hover-sea">Past Papers</Link></li>
        <li><Link href="/lectures" className="gradient-hover-sea">Lectures</Link></li>
        <li><Link href="/generate" className="gradient-hover-sea">Generate Worksheets</Link></li>
        <li><Link href="/#worry-catcher" className="gradient-hover-sea">WorryCatcher</Link></li>
        <li>
          {isClient && <AuthButton />}
        </li>
      </ul>
    </nav>
  )
}
