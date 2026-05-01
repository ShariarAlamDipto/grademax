import { NextResponse } from 'next/server';
import { requireAuth } from '@/lib/apiAuth';
import { getSupabaseAdmin } from '@/lib/supabaseAdmin';
import { normalizeTopicCodes } from '@/lib/topicCodes';
import { trackUsage } from '@/lib/trackUsage';
import { toAbsolutePdfUrl } from '@/lib/pdfUtils';

interface GenerateRequest {
  subjectId?: string;
  topics: string[];
  yearStart?: number;
  yearEnd?: number;
  difficulty?: string;
  limit?: number;
  shuffle?: boolean;
}

interface PageData {
  id: string;
  paper_id: string;
  page_number: number;
  question_number: string;
  topics: string[];
  difficulty: string;
  qp_page_url: string;
  ms_page_url: string | null;
  has_diagram: boolean;
  papers: {
    year: number;
    season: string;
    paper_number: string;
    subject_id: string;
    subjects: {
      code: string;
    };
  };
}

export async function POST(request: Request) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const body: GenerateRequest = await request.json();
    const {
      subjectId,
      topics: rawTopics,
      yearStart,
      yearEnd,
      difficulty,
      limit: rawLimit = 50,
      shuffle = false
    } = body;
    const limit = Math.max(1, Number(rawLimit) || 50);

    if (!rawTopics || rawTopics.length === 0) {
      return NextResponse.json(
        { error: 'Topics are required' },
        { status: 400 }
      );
    }

    // Normalize topic codes: FPM/Physics descriptive codes → numeric IDs; Chemistry/Bio "1.1" style → pass through as-is
    const topics = normalizeTopicCodes(rawTopics);

    const supabase = getSupabaseAdmin() || auth.db;

    // First, get papers that match the subject filter
    let paperQuery = supabase
      .from('papers')
      .select('id, subject_id');

    // Filter by subject if provided
    if (subjectId) {
      paperQuery = paperQuery.eq('subject_id', subjectId);
    }

    // Apply year filters to papers
    if (yearStart) {
      paperQuery = paperQuery.gte('year', yearStart);
    }
    if (yearEnd) {
      paperQuery = paperQuery.lte('year', yearEnd);
    }

    const { data: matchingPapers, error: paperError } = await paperQuery;

    if (paperError) {
      return NextResponse.json(
        { error: 'Failed to fetch papers', details: paperError.message },
        { status: 500 }
      );
    }

    if (!matchingPapers || matchingPapers.length === 0) {
      return NextResponse.json(
        { error: 'No papers found matching the criteria' },
        { status: 404 }
      );
    }

    // Get the paper IDs
    const paperIds = matchingPapers.map(p => p.id);

    // Now query pages that match the criteria
    let query = supabase
      .from('pages')
      .select(`
        id,
        paper_id,
        page_number,
        question_number,
        topics,
        difficulty,
        qp_page_url,
        ms_page_url,
        has_diagram,
        papers (
          year,
          season,
          paper_number,
          subject_id,
          subjects (
            code
          )
        )
      `)
      .eq('is_question', true)
      .not('qp_page_url', 'is', null)
      .in('paper_id', paperIds)  // Filter by matching paper IDs
      .overlaps('topics', topics)  // Array overlap - matches any topic
      .limit(limit);

    // Apply difficulty filter
    if (difficulty) {
      query = query.eq('difficulty', difficulty);
    }

    const { data: pages, error } = await query;

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    if (!pages || pages.length === 0) {
      return NextResponse.json({
        worksheet_id: null,
        pages: [],
        message: 'No questions found matching criteria'
      });
    }

    // Shuffle if requested
    let finalPages = pages as unknown as PageData[];
    if (shuffle) {
      finalPages = [...pages as unknown as PageData[]].sort(() => Math.random() - 0.5);
    }

    // Use subjectId from request, fall back to the value embedded in page data
    const firstPage = pages[0] as unknown as PageData;
    const resolvedSubjectId = subjectId || (firstPage.papers ? firstPage.papers.subject_id : null);

    if (!resolvedSubjectId) {
      return NextResponse.json({ error: 'Could not determine subject' }, { status: 500 });
    }

    // Create worksheet record
    const { data: worksheet, error: worksheetError } = await supabase
      .from('worksheets')
      .insert({
        subject_id: resolvedSubjectId,
        topics,
        year_start: yearStart,
        year_end: yearEnd,
        difficulty,
        total_questions: finalPages.length
      })
      .select('id')
      .single();

    if (worksheetError) {
      return NextResponse.json(
        { error: worksheetError.message },
        { status: 500 }
      );
    }

    // Create worksheet items
    const worksheetItems = finalPages.map((page, index) => ({
      worksheet_id: worksheet.id,
      page_id: page.id,
      sequence: index + 1
    }));

    const { error: itemsError } = await supabase
      .from('worksheet_items')
      .insert(worksheetItems);

    if (itemsError) {
      return NextResponse.json(
        { error: `Failed to save worksheet questions: ${itemsError.message}` },
        { status: 500 }
      );
    }

    // Fire-and-forget usage tracking
    const { data: subjectRow } = await supabase.from('subjects').select('name').eq('id', resolvedSubjectId).single();
    trackUsage({
      user_id: auth.user.id,
      feature: 'worksheet_generate',
      subject_id: resolvedSubjectId,
      subject_name: subjectRow?.name ?? null,
      metadata: { total_questions: finalPages.length, topics },
    });

    // Format response
    const formattedPages = finalPages.map((page) => ({
      id: page.id,
      questionNumber: page.question_number,
      topics: page.topics,
      difficulty: page.difficulty,
      qpPageUrl: toAbsolutePdfUrl(page.qp_page_url)!,
      msPageUrl: toAbsolutePdfUrl(page.ms_page_url),
      hasDiagram: page.has_diagram,
      year: page.papers?.year,
      season: page.papers?.season,
      paper: page.papers?.paper_number
    }));

    return NextResponse.json({
      worksheet_id: worksheet.id,
      pages: formattedPages,
      total_questions: formattedPages.length,
      filters: {
        topics,
        yearStart,
        yearEnd,
        difficulty
      }
    });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
