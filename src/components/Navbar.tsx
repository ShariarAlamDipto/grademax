"use client"
import Link from "next/link"
import { useEffect, useState } from "react"
import NavAuthSection from "./NavAuthSection"

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 768) setMenuOpen(false)
    }
    function handleScroll() {
      setScrolled(window.scrollY > 8)
    }
    window.addEventListener("resize", handleResize)
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => {
      window.removeEventListener("resize", handleResize)
      window.removeEventListener("scroll", handleScroll)
    }
  }, [])

  const navLinks = [
    { href: "/past-papers", label: "Past Papers" },
    { href: "/subjects",    label: "Subjects" },
    { href: "/generate",    label: "Worksheets" },
    { href: "/test-builder",label: "Test Builder" },
    { href: "/lectures",    label: "Lectures" },
    { href: "/dashboard",   label: "Dashboard" },
  ]

  return (
    <nav
      aria-label="Main navigation"
      className="gm-nav"
      style={{ boxShadow: scrolled ? "0 1px 24px rgba(0,0,0,0.6)" : "none" }}
    >
      {/* Main bar */}
      <div className="flex items-center justify-between px-4 md:px-8 py-3.5">

        {/* Logo */}
        <Link
          href="/"
          className="text-xl md:text-2xl font-bold tracking-tight flex-shrink-0"
          style={{ color: "#E5E7EB" }}
        >
          Grade<span style={{ color: "#F59E0B" }}>Max</span>
        </Link>

        {/* Desktop nav links */}
        <ul className="hidden md:flex gap-6 lg:gap-8 text-sm font-medium items-center">
          {navLinks.map(({ href, label }) => (
            <li key={href}>
              <Link href={href} className="gradient-hover-sea">
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Right: auth + CTA + hamburger */}
        <div className="flex items-center gap-3">
          {/* Generate CTA — desktop only */}
          <Link
            href="/generate"
            className="hidden md:inline-flex btn-beacon text-xs px-4 py-2 beacon-pulse"
            style={{ minHeight: "36px", padding: "0.45rem 1rem", borderRadius: "0.5rem" }}
          >
            Generate Worksheet
          </Link>

          <NavAuthSection />

          {/* Hamburger */}
          <button
            className="md:hidden p-2 rounded-lg transition-colors"
            style={{ border: "1px solid #333333", color: "#E5E7EB" }}
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="md:hidden px-4 pb-4" style={{ borderTop: "1px solid #1F2937", background: "#0B1020" }}>
          <ul className="flex flex-col gap-0.5 pt-2">
            {navLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className="gm-link block px-3 py-2.5 rounded-lg text-sm font-medium"
                >
                  {label}
                </Link>
              </li>
            ))}
            <li className="pt-2">
              <Link
                href="/generate"
                onClick={() => setMenuOpen(false)}
                className="block btn-beacon text-sm text-center"
              >
                Generate Worksheet
              </Link>
            </li>
          </ul>
        </div>
      )}
    </nav>
  )
}
