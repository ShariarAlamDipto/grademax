import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export async function GET(req: NextRequest) {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const { searchParams } = new URL(req.url)
  const subjectId = searchParams.get("subjectId")
  if (!subjectId) {
    return NextResponse.json({ error: "subjectId required" }, { status: 400 })
  }

  const db = getSupabaseAdmin()
  if (!db) {
    return NextResponse.json({ error: "Admin client not available" }, { status: 500 })
  }

  // Get all papers for subject
  const { data: papers, error: papersErr } = await db
    .from("papers")
    .select("id")
    .eq("subject_id", subjectId)

  if (papersErr) {
    return NextResponse.json({ error: papersErr.message }, { status: 500 })
  }

  const paperIds = (papers || []).map((p: { id: string }) => p.id)

  if (paperIds.length === 0) {
    return NextResponse.json({
      papers: 0,
      pages: 0,
      pagesWithUrl: 0,
      pagesClassified: 0,
      topicDistribution: {},
      difficultyDistribution: {},
    })
  }

  // Get all pages in batches (Supabase .in() supports up to ~200 items)
  let allPages: Array<{ topics: string[] | null, difficulty: string | null, qp_page_url: string | null }> = []
  for (let i = 0; i < paperIds.length; i += 100) {
    const chunk = paperIds.slice(i, i + 100)
    const { data: pages } = await db
      .from("pages")
      .select("topics, difficulty, qp_page_url")
      .in("paper_id", chunk)
      .eq("is_question", true)
    allPages = allPages.concat(pages || [])
  }

  const pagesWithUrl = allPages.filter(p => p.qp_page_url).length
  const pagesClassified = allPages.filter(p => p.topics && p.topics.length > 0).length

  const topicDistribution: Record<string, number> = {}
  const difficultyDistribution: Record<string, number> = {}

  for (const page of allPages) {
    if (page.topics) {
      for (const t of page.topics) {
        topicDistribution[t] = (topicDistribution[t] || 0) + 1
      }
    }
    if (page.difficulty) {
      difficultyDistribution[page.difficulty] = (difficultyDistribution[page.difficulty] || 0) + 1
    }
  }

  return NextResponse.json({
    papers: paperIds.length,
    pages: allPages.length,
    pagesWithUrl,
    pagesClassified,
    topicDistribution,
    difficultyDistribution,
  })
}
