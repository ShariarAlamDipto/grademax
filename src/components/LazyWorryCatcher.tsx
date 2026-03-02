"use client"
import dynamic from "next/dynamic"

const WorryCatcher = dynamic(() => import("@/components/WorryCatcher"), {
  ssr: false,
  loading: () => (
    <section className="mx-auto max-w-6xl px-2 sm:px-4 pb-16 text-center">
      <h2 className="text-2xl sm:text-3xl md:text-4xl font-semibold mb-4 sm:mb-6">Catch your problems</h2>
      <div className="w-full h-[340px] sm:h-[440px] md:h-[560px] rounded-2xl border border-white/10 bg-gradient-to-b from-white/5 to-transparent animate-pulse" />
    </section>
  ),
})

export default function LazyWorryCatcher() {
  return <WorryCatcher />
}
