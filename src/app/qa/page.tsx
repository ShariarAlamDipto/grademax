"use client"

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabaseClient'
import { useRouter } from 'next/navigation'

interface Ingestion {
  id: string
  paper_id: string
  status: string
  questions_found: number
  parts_found: number
  tags_found: number
  created_at: string
  completed_at: string
  papers: {
    board: string
    level: string
    subject_name: string
    year: number
    season: string
    paper_type: string
    paper_number: string
  }
}

export default function QADashboard() {
  const router = useRouter()
  const [ingestions, setIngestions] = useState<Ingestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedIngestion, setSelectedIngestion] = useState<Ingestion | null>(null)

  useEffect(() => {
    checkAuth()
    loadIngestions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function checkAuth() {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      router.push('/login')
    }
  }

  async function loadIngestions() {
    try {
      setLoading(true)
      const response = await fetch('/api/ingest')
      const data = await response.json()
      
      if (data.success) {
        setIngestions(data.ingestions)
      } else {
        setError(data.errors?.join(', ') || 'Failed to load ingestions')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white/60">Loading ingestions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">❌ {error}</p>
          <button
            onClick={() => loadIngestions()}
            className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-black text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">QA Dashboard</h1>
            <p className="text-white/60">Review and validate ingested papers</p>
          </div>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
          >
            ← Back to Dashboard
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="text-white/60 text-sm mb-1">Total Ingestions</div>
            <div className="text-3xl font-bold">{ingestions.length}</div>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="text-white/60 text-sm mb-1">Questions Found</div>
            <div className="text-3xl font-bold">
              {ingestions.reduce((sum, i) => sum + i.questions_found, 0)}
            </div>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="text-white/60 text-sm mb-1">Parts Found</div>
            <div className="text-3xl font-bold">
              {ingestions.reduce((sum, i) => sum + i.parts_found, 0)}
            </div>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="text-white/60 text-sm mb-1">Tags Generated</div>
            <div className="text-3xl font-bold">
              {ingestions.reduce((sum, i) => sum + i.tags_found, 0)}
            </div>
          </div>
        </div>

        {/* Ingestions Table */}
        <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10 bg-white/5">
                  <th className="text-left p-4 text-sm font-medium text-white/60">Paper</th>
                  <th className="text-left p-4 text-sm font-medium text-white/60">Board</th>
                  <th className="text-left p-4 text-sm font-medium text-white/60">Level</th>
                  <th className="text-right p-4 text-sm font-medium text-white/60">Questions</th>
                  <th className="text-right p-4 text-sm font-medium text-white/60">Parts</th>
                  <th className="text-right p-4 text-sm font-medium text-white/60">Tags</th>
                  <th className="text-left p-4 text-sm font-medium text-white/60">Status</th>
                  <th className="text-left p-4 text-sm font-medium text-white/60">Date</th>
                </tr>
              </thead>
              <tbody>
                {ingestions.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center p-8 text-white/40">
                      No ingestions found
                    </td>
                  </tr>
                ) : (
                  ingestions.map((ingestion) => (
                    <tr
                      key={ingestion.id}
                      className="border-b border-white/10 hover:bg-white/5 cursor-pointer"
                      onClick={() => setSelectedIngestion(ingestion)}
                    >
                      <td className="p-4">
                        <div className="font-medium">
                          {ingestion.papers.subject_name}
                        </div>
                        <div className="text-sm text-white/60">
                          {ingestion.papers.year} {ingestion.papers.season} Paper {ingestion.papers.paper_number}
                        </div>
                      </td>
                      <td className="p-4 text-sm">{ingestion.papers.board}</td>
                      <td className="p-4 text-sm">{ingestion.papers.level}</td>
                      <td className="p-4 text-right text-sm">{ingestion.questions_found}</td>
                      <td className="p-4 text-right text-sm">{ingestion.parts_found}</td>
                      <td className="p-4 text-right text-sm">{ingestion.tags_found}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          ingestion.status === 'completed' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {ingestion.status}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-white/60">
                        {new Date(ingestion.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detail Modal */}
        {selectedIngestion && (
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6 z-50"
            onClick={() => setSelectedIngestion(null)}
          >
            <div
              className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-8 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold mb-2">
                    {selectedIngestion.papers.subject_name}
                  </h2>
                  <p className="text-white/60">
                    {selectedIngestion.papers.board} {selectedIngestion.papers.level} • 
                    {selectedIngestion.papers.year} {selectedIngestion.papers.season} • 
                    Paper {selectedIngestion.papers.paper_number}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedIngestion(null)}
                  className="text-white/60 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-white/5 rounded-lg p-4">
                    <div className="text-white/60 text-sm mb-1">Questions</div>
                    <div className="text-2xl font-bold">{selectedIngestion.questions_found}</div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-4">
                    <div className="text-white/60 text-sm mb-1">Parts</div>
                    <div className="text-2xl font-bold">{selectedIngestion.parts_found}</div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-4">
                    <div className="text-white/60 text-sm mb-1">Tags</div>
                    <div className="text-2xl font-bold">{selectedIngestion.tags_found}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-white/60 text-sm mb-2">Status</div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                      selectedIngestion.status === 'completed' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {selectedIngestion.status}
                    </span>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-white/60 text-sm mb-2">Timestamps</div>
                  <div className="space-y-1 text-sm">
                    <div>Created: {new Date(selectedIngestion.created_at).toLocaleString()}</div>
                    <div>Completed: {new Date(selectedIngestion.completed_at).toLocaleString()}</div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => router.push(`/qa/${selectedIngestion.paper_id}`)}
                    className="flex-1 px-4 py-2 bg-white text-black rounded-lg font-medium hover:bg-white/90"
                  >
                    View Details
                  </button>
                  <button
                    onClick={() => setSelectedIngestion(null)}
                    className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
