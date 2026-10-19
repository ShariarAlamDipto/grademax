// Shown immediately on navigation so the click never looks dead while the
// server renders the page.
export default function TestBuilderLoading() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="h-8 md:h-12 w-64 bg-white/10 rounded-lg animate-pulse mb-2" />
        <div className="h-4 w-96 max-w-full bg-white/5 rounded animate-pulse mb-4 md:mb-8" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 md:gap-3 mb-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-16 md:h-20 rounded-lg border border-gray-700 bg-gray-800/60 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
          <div className="space-y-2">
            {[1, 2, 3, 4, 5, 6, 7].map((i) => (
              <div key={i} className="h-10 rounded-md bg-gray-800/60 animate-pulse" />
            ))}
          </div>
          <div className="lg:col-span-2 space-y-3">
            <div className="h-12 rounded-lg bg-gray-800/60 animate-pulse" />
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 rounded-xl bg-gray-800/40 animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
