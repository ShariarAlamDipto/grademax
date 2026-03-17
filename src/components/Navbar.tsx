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
      window.removeEventListener("scroll", handleScroll, { passive: true } as EventListenerOptions)
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
      style={{ boxShadow: scrolled ? "0 1px 32px rgba(0,0,0,0.7)" : "none" }}
    >
      {/* Main bar */}
      <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 1.25rem", height: "60px" }}>

        {/* Logo — left */}
        <Link
          href="/"
          style={{ color: "#EDF0F7", fontWeight: 800, fontSize: "1.15rem", letterSpacing: "-0.03em", textDecoration: "none", flexShrink: 0, zIndex: 1 }}
        >
          Grade<span style={{ color: "#F59E0B" }}>Max</span>
        </Link>

        {/* Desktop nav links — absolutely centered */}
        <ul
          className="hidden md:flex"
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: "0",
            listStyle: "none",
            margin: 0,
            padding: "0 0.25rem",
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: "99px",
            alignItems: "center",
          }}
        >
          {navLinks.map(({ href, label }) => (
            <li key={href}>
              <Link
                href={href}
                className="gradient-hover-sea"
                style={{ padding: "0.45rem 0.875rem", display: "block", borderRadius: "99px", fontWeight: 500 }}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Right: auth + hamburger */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", zIndex: 1 }}>
          <NavAuthSection />

          {/* Hamburger — mobile only */}
          <button
            className="md:hidden"
            style={{ padding: "0.5rem", borderRadius: "0.625rem", border: "1px solid rgba(255,255,255,0.08)", color: "#EDF0F7", background: "transparent" }}
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
        <div
          className="md:hidden"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)", background: "rgba(6,9,18,0.97)", padding: "0.75rem 1.25rem 1.25rem" }}
        >
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            {navLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className="gm-link"
                  style={{ display: "block", padding: "0.625rem 0.75rem", borderRadius: "0.625rem", fontSize: "0.875rem", fontWeight: 500 }}
                >
                  {label}
                </Link>
              </li>
            ))}
            <li style={{ paddingTop: "0.5rem", borderTop: "1px solid rgba(255,255,255,0.05)", marginTop: "0.25rem" }}>
              <Link
                href="/generate"
                onClick={() => setMenuOpen(false)}
                className="btn-beacon"
                style={{ display: "block", textAlign: "center", fontSize: "0.875rem" }}
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
