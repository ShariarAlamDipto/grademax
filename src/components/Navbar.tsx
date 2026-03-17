"use client"
import Link from "next/link"
import { useEffect, useState } from "react"
import NavAuthSection from "./NavAuthSection"

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)

  // Close mobile menu on resize to desktop
  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 768) setMenuOpen(false)
    }
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/past-papers", label: "Past Papers" },
    { href: "/lectures", label: "Lectures" },
    { href: "/generate", label: "Worksheets" },
    { href: "/test-builder", label: "Test Builder" },
  ]

  return (
    <nav
      aria-label="Main navigation"
      className="fixed top-0 left-0 w-full z-50 bg-[var(--cdm-primary)]/95 backdrop-blur-md shadow-sm border-b border-[#d2aa00] text-[#10162f]"
    >
      {/* Main bar */}
      <div className="flex items-center justify-between px-4 md:px-6 py-3 md:py-4">

        {/* Logo */}
        <Link href="/" className="text-2xl md:text-3xl font-bold tracking-wide flex-shrink-0">
          GradeMax
        </Link>

        {/* Desktop nav links */}
        <ul className="hidden md:flex gap-5 lg:gap-8 text-base lg:text-lg font-semibold items-center">
          {navLinks.map(({ href, label }) => (
            <li key={href}>
              <Link href={href} className="hover:opacity-75 transition-opacity">{label}</Link>
            </li>
          ))}
        </ul>

        {/* Right side: auth + hamburger */}
        <div className="flex items-center gap-2">
          <NavAuthSection />

          {/* Hamburger — mobile only */}
          <button
            className="md:hidden p-2 rounded-lg border border-[#8f7300] hover:bg-black/10 transition-colors"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="md:hidden border-t border-[#d2aa00] bg-[var(--cdm-primary-soft)] px-4 py-3">
          <ul className="flex flex-col gap-0.5">
            {navLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className="block px-3 py-2.5 rounded-lg text-base font-semibold text-[#10162f] hover:bg-black/5 transition-colors"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </nav>
  )
}
