import { supabase } from '../../lib/supabaseClient'

export default async function PastPapers() {
  console.log('Supabase client:', supabase)

  return (
    <main className="min-h-screen bg-black text-white p-8">
      <h1 className="text-4xl mb-8">Past Papers</h1>
      <p>Check your terminal — Supabase client should be logged there.</p>
    </main>
  )
}
