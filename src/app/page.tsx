// src/app/page.tsx
import WorryCatcher from "@/components/WorryCatcher"

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white">
    <div className="text-2xl md:text-4xl font-bold text-white text-center mb-6 mt-20">
      All IGCSE and IAL solution under one roof
    </div>
      <WorryCatcher />
    </main>
  )
}
