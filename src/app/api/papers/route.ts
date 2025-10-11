/**
 * API Route: /api/papers
 * 
 * Get papers with optional filtering
 */

import { NextRequest, NextResponse } from 'next/server'
import { getSupabaseServer } from '@/lib/supabaseServer'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    // Check authentication
    const supabase = getSupabaseServer()
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { success: false, errors: ['Unauthorized'] },
        { status: 401 }
      )
    }
    
    // Parse query parameters
    const searchParams = request.nextUrl.searchParams
    const board = searchParams.get('board')
    const level = searchParams.get('level')
    const subject = searchParams.get('subject')
    const year = searchParams.get('year') ? parseInt(searchParams.get('year')!) : undefined
    const season = searchParams.get('season')
    const limit = searchParams.get('limit') ? parseInt(searchParams.get('limit')!) : 50
    
    // Build query
    let query = supabase
      .from('papers')
      .select(`
        *,
        questions (
          id,
          question_number,
          total_marks,
          difficulty,
          difficulty_score
        )
      `)
      .order('year', { ascending: false })
      .order('season', { ascending: false })
      .limit(limit)
    
    // Apply filters
    if (board) query = query.eq('board', board)
    if (level) query = query.eq('level', level)
    if (subject) query = query.eq('subject_code', subject)
    if (year) query = query.eq('year', year)
    if (season) query = query.eq('season', season)
    
    const { data: papers, error } = await query
    
    if (error) {
      return NextResponse.json(
        { success: false, errors: [error.message] },
        { status: 500 }
      )
    }
    
    return NextResponse.json({
      success: true,
      papers: papers || [],
      count: papers?.length || 0
    })
    
  } catch (error) {
    console.error('❌ GET papers error:', error)
    return NextResponse.json(
      {
        success: false,
        errors: [error instanceof Error ? error.message : 'Unknown error']
      },
      { status: 500 }
    )
  }
}

/**
 * GET /api/papers/[id]
 * 
 * Get specific paper with all questions and parts
 */
export async function getPaper(paperId: string) {
  const supabase = getSupabaseServer()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  
  if (authError || !user) {
    return NextResponse.json(
      { success: false, errors: ['Unauthorized'] },
      { status: 401 }
    )
  }
  
  const { data: paper, error } = await supabase
    .from('papers')
    .select(`
      *,
      questions (
        *,
        question_parts (*),
        question_tags (*)
      )
    `)
    .eq('id', paperId)
    .single()
  
  if (error) {
    return NextResponse.json(
      { success: false, errors: [error.message] },
      { status: 500 }
    )
  }
  
  if (!paper) {
    return NextResponse.json(
      { success: false, errors: ['Paper not found'] },
      { status: 404 }
    )
  }
  
  return NextResponse.json({
    success: true,
    paper
  })
}
