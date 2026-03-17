"use client"
import Link from "next/link"
import { useEffect, useRef, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import ThemeToggle from "./ThemeToggle"

export default function Navbar() {
  const { user, displayName, avatarUrl, loading, isTeacher, isAdmin, signOut } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Close mobile menu on resize to desktop
  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 768) setMenuOpen(false)
    }
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  const initials = displayName
    ? displayName.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2)
    : "?"

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
      className="fixed top-0 left-0 w-full z-50 bg-white/95 dark:bg-black/80 backdrop-blur-md shadow-sm border-b border-gray-200 dark:border-white/10 text-gray-900 dark:text-white"
    >
      {/* Main bar */}
      <div className="flex items-center justify-between px-4 md:px-6 py-3 md:py-4">

        {/* Logo */}
        <Link href="/" className="text-2xl md:text-3xl font-bold tracking-wide flex-shrink-0">
          GradeMax
        </Link>

        {/* Desktop nav links */}
        <ul className="hidden md:flex gap-5 lg:gap-8 text-sm font-medium items-center">
          {navLinks.map(({ href, label }) => (
            <li key={href}>
              <Link href={href} className="gradient-hover-sea">{label}</Link>
            </li>
          ))}
        </ul>

        {/* Right side: theme toggle + auth + hamburger */}
        <div className="flex items-center gap-2">

          {/* Theme toggle */}
          <ThemeToggle />

          {/* Auth */}
          {!loading && (
            user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen((v) => !v)}
                  className="flex items-center gap-2 rounded-full border border-gray-200 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 pl-1 pr-2 py-1 transition-colors"
                >
                  {avatarUrl ? (
                    <img
                      src={avatarUrl}
                      alt={displayName}
                      className="w-7 h-7 rounded-full object-cover"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-black/10 dark:bg-white/20 flex items-center justify-center text-xs font-semibold">
                      {initials}
                    </div>
                  )}
                  <span className="text-sm font-medium hidden sm:inline max-w-[100px] truncate">
                    {displayName}
                  </span>
                  <svg className="w-3.5 h-3.5 text-gray-400 dark:text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-gray-900 shadow-xl py-2 z-50">
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-white/10">
                      <p className="text-sm font-semibold truncate">{displayName}</p>
                      <p className="text-xs truncate text-gray-500 dark:text-white/50">{user.email}</p>
                    </div>
                    <Link
                      href="/profile"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                    >
                      <svg className="w-4 h-4 text-gray-400 dark:text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      My Profile
                    </Link>
                    <Link
                      href="/dashboard"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                    >
                      <svg className="w-4 h-4 text-gray-400 dark:text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                      </svg>
                      Dashboard
                    </Link>
                    {isTeacher && (
                      <Link
                        href="/dashboard/teacher"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                      >
                        <svg className="w-4 h-4 text-gray-400 dark:text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                        Teacher Panel
                      </Link>
                    )}
                    {isAdmin && (
                      <Link
                        href="/dashboard/admin"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                      >
                        <svg className="w-4 h-4 text-gray-400 dark:text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Admin Panel
                      </Link>
                    )}
                    <div className="border-t border-gray-200 dark:border-white/10 mt-1 pt-1">
                      <button
                        onClick={() => { setDropdownOpen(false); signOut() }}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/5 transition-colors w-full"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className="rounded-lg bg-gray-900 text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors"
              >
                Sign In
              </Link>
            )
          )}

          {/* Hamburger — mobile only */}
          <button
            className="md:hidden p-2 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
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
        <div className="md:hidden border-t border-gray-200 dark:border-white/10 bg-white dark:bg-gray-950 px-4 py-3">
          <ul className="flex flex-col gap-0.5">
            {navLinks.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className="block px-3 py-2.5 rounded-lg text-base font-semibold text-gray-900 hover:bg-gray-100 dark:text-white dark:hover:bg-white/5 transition-colors"
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
