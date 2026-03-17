"use client"
import Link from "next/link"
import { useEffect, useState } from "react"
import NavAuthSection from "./NavAuthSection"
import ThemeToggle from "./ThemeToggle"

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 1024) setMenuOpen(false)
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

  // Always visible on all screen sizes
  const coreLinks = [
    { href: "/past-papers", label: "Past Papers" },
    { href: "/generate",    label: "Worksheets" },
    { href: "/test-builder",label: "Test Builder" },
  ]

  // Only visible on larger screens (lg+)
  const extraLinks = [
    { href: "/subjects",    label: "Subjects" },
    { href: "/lectures",    label: "Lectures" },
    { href: "/dashboard",   label: "Dashboard" },
  ]

  const allLinks = [...coreLinks, ...extraLinks]

  return (
    <nav
      aria-label="Main navigation"
      className="gm-nav"
      style={{ boxShadow: scrolled ? "0 1px 32px rgba(0,0,0,0.5)" : "none" }}
    >
      {/* Main bar */}
      <div style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 1.5rem",
        height: "68px",
      }}>

        {/* Logo */}
        <Link
          href="/"
          style={{
            color: "var(--gm-text)",
            fontWeight: 800,
            fontSize: "1.35rem",
            letterSpacing: "-0.04em",
            textDecoration: "none",
            flexShrink: 0,
            zIndex: 1,
            lineHeight: 1,
          }}
        >
          Grade<span style={{ color: "var(--gm-amber)" }}>Max</span>
        </Link>

        {/* Desktop nav pill — absolutely centered */}
        <ul
          className="hidden lg:flex"
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: 0,
            listStyle: "none",
            margin: 0,
            padding: "0 0.3rem",
            background: "var(--gm-card-bg)",
            border: "1px solid var(--gm-border-2)",
            borderRadius: "99px",
            alignItems: "center",
            whiteSpace: "nowrap",
          }}
        >
          {allLinks.map(({ href, label }) => (
            <li key={href}>
              <Link
                href={href}
                className="gradient-hover-sea"
                style={{
                  padding: "0.5rem 1rem",
                  display: "block",
                  borderRadius: "99px",
                }}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Tablet: core 3 links always visible */}
        <ul
          className="hidden sm:flex lg:hidden"
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: 0,
            listStyle: "none",
            margin: 0,
            padding: "0 0.3rem",
            background: "var(--gm-card-bg)",
            border: "1px solid var(--gm-border-2)",
            borderRadius: "99px",
            alignItems: "center",
            whiteSpace: "nowrap",
          }}
        >
          {coreLinks.map(({ href, label }) => (
            <li key={href}>
              <Link
                href={href}
                className="gradient-hover-sea"
                style={{
                  padding: "0.45rem 0.875rem",
                  display: "block",
                  borderRadius: "99px",
                  fontSize: "0.82rem",
                }}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Mobile: core 3 links (smaller) */}
        <ul
          className="flex sm:hidden"
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: 0,
            listStyle: "none",
            margin: 0,
            padding: "0 0.2rem",
            background: "var(--gm-card-bg)",
            border: "1px solid var(--gm-border-2)",
            borderRadius: "99px",
            alignItems: "center",
            whiteSpace: "nowrap",
          }}
        >
          {coreLinks.map(({ href, label }) => (
            <li key={href}>
              <Link
                href={href}
                className="gradient-hover-sea"
                style={{
                  padding: "0.35rem 0.55rem",
                  display: "block",
                  borderRadius: "99px",
                  fontSize: "0.7rem",
                }}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Right: theme toggle + auth + hamburger */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", zIndex: 1, flexShrink: 0 }}>
          <ThemeToggle />
          <NavAuthSection />

          {/* Hamburger — hidden on lg+ */}
          <button
            className="lg:hidden"
            style={{
              padding: "0.45rem",
              borderRadius: "0.625rem",
              border: "1px solid var(--gm-border-2)",
              color: "var(--gm-text)",
              background: "transparent",
              cursor: "pointer",
              flexShrink: 0,
            }}
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

      {/* Mobile/tablet drawer — shows extra links only (core are always in pill) */}
      {menuOpen && (
        <div
          className="lg:hidden"
          style={{
            borderTop: "1px solid var(--gm-border)",
            background: "var(--gm-nav-bg)",
            padding: "0.75rem 1.5rem 1.25rem",
          }}
        >
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "0.2rem" }}>
            {allLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  style={{
                    display: "block",
                    padding: "0.6rem 0.75rem",
                    borderRadius: "0.625rem",
                    fontSize: "0.9rem",
                    fontWeight: 500,
                    color: "var(--gm-text-2)",
                    textDecoration: "none",
                    transition: "color 0.15s, background 0.15s",
                  }}
                  className="gm-link"
                >
                  {label}
                </Link>
              </li>
            ))}
            <li style={{ paddingTop: "0.5rem", borderTop: "1px solid var(--gm-border)", marginTop: "0.25rem" }}>
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
