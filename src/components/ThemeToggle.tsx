"use client"

export default function ThemeToggle() {
  function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark')
    const next = isDark ? 'light' : 'dark'
    document.documentElement.classList.remove('dark', 'light')
    document.documentElement.classList.add(next)
    localStorage.setItem('theme', next)
  }

  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle theme"
      className="p-2 rounded-full border border-gray-200 dark:border-white/10 bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/20 text-gray-700 dark:text-white transition-colors"
    >
      {/* Moon icon — shown in dark mode */}
      <svg className="hidden dark:block" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path d="M21 12.79A9 9 0 1112.21 3a7 7 0 000 14A9 9 0 0021 12.79z" />
      </svg>
      {/* Sun icon — shown in light mode */}
      <svg className="block dark:hidden" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="5" />
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
      </svg>
    </button>
  )
}
