export default function GenerateLoading() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Title skeleton */}
        <div className="h-8 md:h-12 w-64 bg-white/10 rounded-lg animate-pulse mb-2" />
        <div className="h-4 w-96 bg-white/5 rounded animate-pulse mb-4 md:mb-8" />

        {/* Filters panel skeleton */}
        <div className="bg-gray-800 bg-opacity-80 rounded-xl md:rounded-2xl p-4 md:p-8 border border-gray-700">
          {/* Subject selection */}
          <div className="mb-4 md:mb-8">
            <div className="h-6 w-32 bg-white/10 rounded animate-pulse mb-3 md:mb-4" />
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-5 gap-2 md:gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 md:h-24 rounded-lg md:rounded-xl border-2 border-gray-600 bg-gray-700/50 animate-pulse" />
              ))}
            </div>
          </div>

          {/* Topics section */}
          <div className="mb-4 md:mb-8">
            <div className="h-6 w-28 bg-white/10 rounded animate-pulse mb-3 md:mb-4" />
            <div className="space-y-2">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-10 md:h-12 rounded-md bg-gray-700/30 animate-pulse" />
              ))}
            </div>
          </div>

          {/* Filters row */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-6 mb-4 md:mb-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 md:h-14 rounded-lg bg-gray-700/50 animate-pulse" />
            ))}
          </div>

          {/* Generate button */}
          <div className="h-12 md:h-14 w-full rounded-xl bg-blue-500/20 animate-pulse" />
        </div>
      </div>
    </div>
  )
}
