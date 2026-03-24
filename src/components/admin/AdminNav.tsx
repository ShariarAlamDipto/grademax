"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"

const NAV_ITEMS = [
  { href: "/admin", label: "Overview", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { href: "/admin/papers", label: "Papers", icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
  { href: "/admin/scraper", label: "Scraper", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" },
  { href: "/admin/subjects", label: "Subjects", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" },
  { href: "/admin/users", label: "Users", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" },
  { href: "/admin/analytics", label: "Analytics", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { href: "/admin/tagger", label: "Tagger", icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" },
]

export default function AdminNav() {
  const pathname = usePathname()

  return (
    <aside style={{
      width: "220px",
      flexShrink: 0,
      borderRight: "1px solid var(--gm-border)",
      background: "var(--gm-surface)",
      display: "flex",
      flexDirection: "column",
      padding: "1.5rem 0",
      position: "sticky",
      top: 0,
      height: "100vh",
      overflowY: "auto",
    }}>
      {/* Logo */}
      <div style={{ padding: "0 1.25rem 1.5rem", borderBottom: "1px solid var(--gm-border)", marginBottom: "0.75rem" }}>
        <p style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-amber)", marginBottom: "0.25rem" }}>
          GradeMax
        </p>
        <p style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.01em" }}>
          Admin Portal
        </p>
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1, padding: "0 0.75rem" }}>
        {NAV_ITEMS.map(item => {
          const isActive = item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.625rem",
                padding: "0.5rem 0.625rem",
                borderRadius: "0.5rem",
                marginBottom: "0.125rem",
                fontSize: "0.8rem",
                fontWeight: isActive ? 600 : 400,
                color: isActive ? "var(--gm-text)" : "var(--gm-text-3)",
                background: isActive ? "var(--gm-bg)" : "transparent",
                textDecoration: "none",
                transition: "all 0.15s ease",
              }}
            >
              <svg style={{ width: "1rem", height: "1rem", flexShrink: 0, color: isActive ? "var(--gm-blue)" : "var(--gm-text-3)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d={item.icon} />
              </svg>
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Back to site */}
      <div style={{ padding: "0.75rem", borderTop: "1px solid var(--gm-border)", marginTop: "auto" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "var(--gm-text-3)", textDecoration: "none" }}>
          <svg style={{ width: "0.875rem", height: "0.875rem" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to site
        </Link>
      </div>
    </aside>
  )
}
