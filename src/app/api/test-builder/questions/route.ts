import { NextResponse } from 'next/server';
import { requireAuth } from '@/lib/apiAuth';
import { getSupabaseAdmin } from '@/lib/supabaseAdmin';
import { normalizeTopicCodes } from '@/lib/topicCodes';
import { toAbsolutePdfUrl } from '@/lib/pdfUtils';
import { getQuestionMarks } from '@/lib/questionMarks';

/**
 * GET /api/test-builder/questions
 * 
 * Browse questions with filters for the test builder.
 * Returns paginated question cards with metadata.
 * 
 * Query params:
 *   subjectId  - required: UUID of the subject
 *   topics     - optional: comma-separated topic codes (e.g., "1b,1c,2a")
 *   difficulty - optional: "easy" | "medium" | "hard"
 *   yearStart  - optional: minimum year
 *   yearEnd    - optional: maximum year
 *   page       - optional: page number (default 1)
 *   limit      - optional: items per page (default 20, max 50)
 */
export async function GET(request: Request) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const url = new URL(request.url);
    const subjectId = url.searchParams.get('subjectId');
    const topicsParam = url.searchParams.get('topics');
    const difficulty = url.searchParams.get('difficulty');
    const yearStart = url.searchParams.get('yearStart');
    const yearEnd = url.searchParams.get('yearEnd');
    const page = Math.max(1, parseInt(url.searchParams.get('page') || '1') || 1);
    const limit = Math.min(50, Math.max(1, parseInt(url.searchParams.get('limit') || '20') || 20));

    if (!subjectId) {
      return NextResponse.json(
        { error: 'subjectId is required' },
        { status: 400 }
      );
    }

    const supabase = getSupabaseAdmin() || auth.db;

    // Step 1: Get paper IDs for this subject (with optional year filter)
    let paperQuery = supabase
      .from('papers')
      .select('id')
      .eq('subject_id', subjectId);

    if (yearStart) {
      paperQuery = paperQuery.gte('year', parseInt(yearStart));
    }
    if (yearEnd) {
      paperQuery = paperQuery.lte('year', parseInt(yearEnd));
    }

    const { data: papers, error: paperError } = await paperQuery;

    if (paperError) {
      return NextResponse.json(
        { error: 'Failed to fetch papers', details: paperError.message },
        { status: 500 }
      );
    }

    if (!papers || papers.length === 0) {
      return NextResponse.json({
        questions: [],
        pagination: { page, limit, total: 0, totalPages: 0 }
      });
    }

    const topicCodes = topicsParam
      ? normalizeTopicCodes(topicsParam.split(',').map(t => t.trim()).filter(Boolean))
      : [];

    const offset = (page - 1) * limit;

    // Single query: fetch page data + total count in one round-trip
    let dataQuery = supabase
      .from('pages')
      .select(`
        id,
        paper_id,
        page_number,
        question_number,
        topics,
        difficulty,
        confidence,
        qp_page_url,
        ms_page_url,
        has_diagram,
        text_excerpt,
        papers!inner (
          year,
          season,
          paper_number,
          subject_id
        )
      `, { count: 'exact' })
      .eq('is_question', true)
      .not('qp_page_url', 'is', null)
      // Filter on the joined paper instead of `.in('paper_id', [...ids])`:
      // Cambridge 0625's 397 paper ids made a ~15 KB URL that failed with
      // "TypeError: fetch failed" (9 Nov 2026).
      .eq('papers.subject_id', subjectId)
      // page_number repeats across papers, so it alone gives Postgres no fixed
      // order: OFFSET paging then showed some questions on two pages and never
      // showed others. paper_id + the unique id make the order total.
      .order('page_number', { ascending: true })
      .order('paper_id', { ascending: true })
      .order('id', { ascending: true })
      .range(offset, offset + limit - 1);

    if (yearStart) dataQuery = dataQuery.gte('papers.year', parseInt(yearStart));
    if (yearEnd) dataQuery = dataQuery.lte('papers.year', parseInt(yearEnd));
    if (topicCodes.length > 0) dataQuery = dataQuery.overlaps('topics', topicCodes);
    if (difficulty) dataQuery = dataQuery.eq('difficulty', difficulty);

    const { data: pages, count, error: pagesError } = await dataQuery;

    // PostgREST answers 416 (PGRST103) for a page past the end, e.g. a stale
    // link after questions were removed. That is an empty page, not a failure.
    if (pagesError?.code === 'PGRST103') {
      return NextResponse.json({
        questions: [],
        pagination: { page, limit, total: 0, totalPages: 0 }
      });
    }

    if (pagesError) {
      return NextResponse.json(
        { error: 'Failed to fetch questions', details: pagesError.message },
        { status: 500 }
      );
    }

    const total = count || 0;
    const totalPages = Math.ceil(total / limit);

    // Step 4: Format response
    interface PaperData {
      year: number;
      season: string;
      paper_number: string;
      subject_id: string;
    }

    interface PageRow {
      id: string;
      paper_id: string;
      page_number: number;
      question_number: string;
      topics: string[];
      difficulty: string;
      confidence: number | null;
      qp_page_url: string;
      ms_page_url: string | null;
      has_diagram: boolean;
      text_excerpt: string | null;
      papers: PaperData;
    }

    const questions = ((pages || []) as unknown as PageRow[]).map((p) => ({
      id: p.id,
      questionNumber: p.question_number || String(p.page_number),
      marks: getQuestionMarks(p.paper_id, p.question_number),
      topics: p.topics || [],
      difficulty: p.difficulty || 'unknown',
      qpPageUrl: toAbsolutePdfUrl(p.qp_page_url)!,
      msPageUrl: toAbsolutePdfUrl(p.ms_page_url),
      hasDiagram: p.has_diagram || false,
      textExcerpt: p.text_excerpt || '',
      year: p.papers?.year,
      season: p.papers?.season,
      paper: p.papers?.paper_number,
    }));

    return NextResponse.json({
      questions,
      pagination: {
        page,
        limit,
        total,
        totalPages,
      }
    });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
