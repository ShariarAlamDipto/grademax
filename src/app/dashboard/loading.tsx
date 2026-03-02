export default function DashboardLoading() {
  return (
    <main className="min-h-screen bg-black text-white px-6 pb-16">
      {/* Header skeleton */}
      <div className="max-w-6xl mx-auto py-6 mb-2">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-48 rounded-md bg-white/10 animate-pulse" />
            <div className="h-4 w-56 rounded-md bg-white/5 animate-pulse mt-2" />
          </div>
          <div className="h-9 w-24 rounded-lg bg-white/10 animate-pulse" />
        </div>
      </div>

      <div className="max-w-6xl mx-auto grid gap-8 md:grid-cols-3">
        {/* Left column skeletons */}
        <div className="md:col-span-1 space-y-6">
          {/* Level & Goal */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-4">
            <div className="h-5 w-24 rounded bg-white/10 animate-pulse" />
            <div className="flex gap-2">
              <div className="h-9 w-16 rounded-md bg-white/10 animate-pulse" />
              <div className="h-9 w-16 rounded-md bg-white/10 animate-pulse" />
            </div>
            <div className="h-4 w-20 rounded bg-white/10 animate-pulse" />
            <div className="h-8 w-24 rounded-md bg-white/10 animate-pulse" />
          </div>
          {/* Subjects */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-3">
            <div className="h-5 w-28 rounded bg-white/10 animate-pulse" />
            <div className="h-4 w-48 rounded bg-white/5 animate-pulse" />
          </div>
        </div>

        {/* Right column skeletons */}
        <div className="md:col-span-2 space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Timer */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 flex items-center justify-center">
              <div className="w-40 h-40 rounded-full bg-white/10 animate-pulse" />
            </div>
            {/* Chart */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="h-4 w-36 rounded bg-white/10 animate-pulse mb-2" />
              <div className="h-64 rounded-lg bg-white/5 animate-pulse" />
            </div>
          </div>
          {/* Papers */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-3">
            <div className="h-5 w-20 rounded bg-white/10 animate-pulse" />
            <div className="h-2 w-full rounded-full bg-white/10 animate-pulse" />
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-12 rounded-md bg-white/5 animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
