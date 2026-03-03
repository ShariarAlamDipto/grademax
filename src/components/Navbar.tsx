"use client"
import Link from "next/link"
import { useCallback, useRef, useState } from "react"
import { useAuth } from "@/context/AuthContext"

export default function Navbar() {
  const { user, displayName, avatarUrl, loading, signOut } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
      setDropdownOpen(false)
    }
  }, [])

  // Use a ref-based approach to avoid re-registering on every render
  const listenerRef = useRef(false)
  if (!listenerRef.current && typeof document !== "undefined") {
    document.addEventListener("mousedown", handleClickOutside)
    listenerRef.current = true
  }

  const initials = displayName
    ? displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?"

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

        {/* Auth / Profile */}
        <li>
          {!loading && (
            user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen((v) => !v)}
                  className="flex items-center gap-2 rounded-full border border-white/20 bg-white/5 pl-1 pr-3 py-1 hover:bg-white/10 transition-colors"
                >
                  {avatarUrl ? (
                    <img
                      src={avatarUrl}
                      alt={displayName}
                      className="w-8 h-8 rounded-full object-cover"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-xs font-semibold">
                      {initials}
                    </div>
                  )}
                  <span className="text-sm font-medium hidden md:inline max-w-[120px] truncate">
                    {displayName}
                  </span>
                  <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-xl border border-white/10 bg-black/95 backdrop-blur-md shadow-xl py-2 z-50">
                    <div className="px-4 py-3 border-b border-white/10">
                      <p className="text-sm font-semibold truncate">{displayName}</p>
                      <p className="text-xs text-white/50 truncate">{user.email}</p>
                    </div>
                    <Link
                      href="/profile"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-white/5 transition-colors"
                    >
                      <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      My Profile
                    </Link>
                    <Link
                      href="/dashboard"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-white/5 transition-colors"
                    >
                      <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                      </svg>
                      Dashboard
                    </Link>
                    <div className="border-t border-white/10 mt-1 pt-1">
                      <button
                        onClick={() => { setDropdownOpen(false); signOut() }}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-white/5 transition-colors w-full"
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
                className="rounded-lg bg-white text-black px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
              >
                Sign In
              </Link>
            )
          )}
        </li>
      </ul>
    </nav>
  )
}
