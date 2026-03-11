"use client"
import Link from "next/link"
import { useEffect, useRef, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { useTheme } from '@/context/ThemeContext'

export default function Navbar() {
  const { user, displayName, avatarUrl, loading, isTeacher, isAdmin, signOut } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { theme, toggleTheme } = useTheme();

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

  const initials = displayName
    ? displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?"

  const bg = theme === 'dark' ? 'bg-black/70' : 'bg-white/90';
  const text = theme === 'dark' ? 'text-white' : 'text-gray-900';
  const border = theme === 'dark' ? 'border-white/20' : 'border-gray-200';
  return (
    <nav aria-label="Main navigation" className={`flex flex-col md:flex-row items-center justify-between px-4 md:px-6 py-4 md:py-5 ${bg} backdrop-blur-md fixed top-0 left-0 w-full z-50 shadow-lg ${text}`}> 
      <div className="flex items-center gap-4">
        <div className="text-2xl md:text-4xl font-bold tracking-wide mb-3 md:mb-0 text-center w-full md:w-auto">
          <Link href="/">GradeMax</Link>
        </div>
        <button
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="ml-2 p-2 rounded-full border border-white/20 bg-white/5 hover:bg-white/10 transition-colors text-lg"
        >
          {theme === 'dark' ? (
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 0112.21 3a7 7 0 000 14A9 9 0 0021 12.79z" /></svg>
          ) : (
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" /></svg>
          )}
        </button>
      </div>
      <ul className="flex flex-wrap gap-3 md:gap-10 text-sm md:text-xl font-semibold items-center justify-center w-full md:w-auto">
        <li><Link href="/" className="gradient-hover-sea">Home</Link></li>
        <li><Link href="/dashboard" className="gradient-hover-sea">Dashboard</Link></li>
        <li><Link href="/past-papers" className="gradient-hover-sea">Past Papers</Link></li>
        <li><Link href="/lectures" className="gradient-hover-sea">Lectures</Link></li>
        <li><Link href="/generate" className="gradient-hover-sea">Worksheets</Link></li>
        <li><Link href="/test-builder" className="gradient-hover-sea">Test Builder</Link></li>

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
                    {isTeacher && (
                      <Link
                        href="/dashboard/teacher"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-white/5 transition-colors"
                      >
                        <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                        Teacher Panel
                      </Link>
                    )}
                    {isAdmin && (
                      <Link
                        href="/dashboard/admin"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-white/5 transition-colors"
                      >
                        <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Admin Panel
                      </Link>
                    )}
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
