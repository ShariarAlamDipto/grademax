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
      window.removeEventListener("scroll", handleScroll)
    }
  }, [])

  const coreLinks = [
    { href: "/past-papers",  label: "Past Papers" },
    { href: "/generate",     label: "Worksheets" },
    { href: "/test-builder", label: "Test Builder" },
  ]

  const extraLinks = [
    { href: "/subjects",  label: "Subjects" },
    { href: "/lectures",  label: "Lectures" },
    { href: "/dashboard", label: "Dashboard" },
  ]

  const allLinks = [...coreLinks, ...extraLinks]

  const pillBase: React.CSSProperties = {
    listStyle: "none",
    margin: 0,
    padding: "0 0.3rem",
    background: "var(--gm-card-bg)",
    border: "1px solid var(--gm-border-2)",
    borderRadius: "99px",
    alignItems: "center",
    whiteSpace: "nowrap",
    gap: 0,
  }

  return (
    <nav
      aria-label="Main navigation"
      className="gm-nav"
      style={{ boxShadow: scrolled ? "0 2px 24px rgba(0,0,0,0.35)" : "none" }}
    >
      {/* ── Main bar ── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "auto 1fr auto",
        alignItems: "center",
        padding: "0 1.25rem",
        height: "68px",
        gap: "0.75rem",
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
            lineHeight: 1,
            whiteSpace: "nowrap",
          }}
        >
          Grade<span style={{ color: "var(--gm-amber)" }}>Max</span>
        </Link>

        {/* Center pill — Tailwind controls display; NO inline display property */}
        <div style={{ display: "flex", justifyContent: "center", minWidth: 0, overflow: "hidden" }}>

          {/* Desktop (lg+): all 6 links */}
          <ul className="hidden lg:flex" style={pillBase}>
            {allLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="gradient-hover-sea"
                  style={{ padding: "0.5rem 0.85rem", display: "block", borderRadius: "99px", fontSize: "0.875rem" }}
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>

          {/* Tablet (sm–lg): core 3 only */}
          <ul className="hidden sm:flex lg:hidden" style={pillBase}>
            {coreLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="gradient-hover-sea"
                  style={{ padding: "0.45rem 0.9rem", display: "block", borderRadius: "99px", fontSize: "0.83rem" }}
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>

          {/* Mobile (<sm): nothing in center row — links shown in row below */}
        </div>

        {/* Right: theme toggle + auth + hamburger */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexShrink: 0 }}>
          <ThemeToggle />
          <NavAuthSection />
          <button
            className="lg:hidden"
            style={{
              padding: "0.45rem",
              borderRadius: "0.5rem",
              border: "1px solid var(--gm-border-2)",
              color: "var(--gm-text)",
              background: "transparent",
              cursor: "pointer",
              flexShrink: 0,
              lineHeight: 0,
            }}
            onClick={() => setMenuOpen(v => !v)}
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

      {/* ── Mobile core-links row (only on xs, hidden sm+) ── */}
      <div
        className="flex sm:hidden"
        style={{
          borderTop: "1px solid var(--gm-border)",
          padding: "0.5rem 1rem",
          justifyContent: "space-around",
          background: "var(--gm-nav-bg)",
          gap: "0.375rem",
        }}
      >
        {coreLinks.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="gradient-hover-sea"
            style={{
              padding: "0.35rem 0.65rem",
              borderRadius: "99px",
              fontSize: "0.72rem",
              fontWeight: 500,
              whiteSpace: "nowrap",
              background: "var(--gm-card-bg)",
              border: "1px solid var(--gm-border-2)",
              textDecoration: "none",
              flex: "1 1 0",
              textAlign: "center",
              maxWidth: "120px",
            }}
          >
            {label}
          </Link>
        ))}
      </div>

      {/* ── Drawer (mobile/tablet, hidden lg+) ── */}
      {menuOpen && (
        <div
          className="lg:hidden"
          style={{
            borderTop: "1px solid var(--gm-border)",
            background: "var(--gm-nav-bg)",
            padding: "0.75rem 1.25rem 1.25rem",
          }}
        >
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "0.15rem" }}>
            {allLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className="gm-link"
                  style={{
                    display: "block",
                    padding: "0.6rem 0.75rem",
                    borderRadius: "0.5rem",
                    fontSize: "0.9rem",
                    fontWeight: 500,
                    color: "var(--gm-text-2)",
                    textDecoration: "none",
                  }}
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
