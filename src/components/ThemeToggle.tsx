"use client"
import { useEffect, useState } from "react"

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(true)

  useEffect(() => {
    // Read current theme from DOM (set by inline script before hydration)
    setIsDark(document.documentElement.classList.contains("dark"))
  }, [])

  function toggleTheme() {
    const next = isDark ? "light" : "dark"
    document.documentElement.classList.remove("dark", "light")
    document.documentElement.classList.add(next)
    localStorage.setItem("theme", next)
    setIsDark(!isDark)
  }

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="theme-toggle"
      title={isDark ? "Light mode" : "Dark mode"}
    >
      {isDark ? (
        // Sun icon — click to go light
        <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      ) : (
        // Moon icon — click to go dark
        <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M21 12.79A9 9 0 1112.21 3a7 7 0 000 14A9 9 0 0021 12.79z" />
        </svg>
      )}
    </button>
  )
}
