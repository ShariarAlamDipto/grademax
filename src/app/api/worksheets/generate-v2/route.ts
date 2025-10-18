import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getUsageMeterService } from '@/lib/usageMeter';
import { getAuditLogger } from '@/lib/auditLogger';
import { cookies } from 'next/headers';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

interface GenerateRequest {
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
    const body: GenerateRequest = await request.json();
    const {
      topics,
      yearStart,
      yearEnd,
      difficulty,
      limit = 50,
      shuffle = false
    } = body;

    if (!topics || topics.length === 0) {
      return NextResponse.json(
        { error: 'Topics are required' },
        { status: 400 }
      );
    }

    // Get authenticated user (Phase 1)
    const cookieStore = await cookies();
    const authCookie = cookieStore.get('sb-tybaetnvnfgniotdfxze-auth-token');
    
    let userId: string | null = null;
    let userEmail: string | null = null;
    
    if (authCookie) {
      const supabaseAuth = createClient(supabaseUrl, supabaseServiceKey);
      const { data: { user } } = await supabaseAuth.auth.getUser(authCookie.value.split('-')[0]);
      userId = user?.id || null;
      userEmail = user?.email || null;
    }

    // Check quota (Phase 1)
    if (userId) {
      const meter = getUsageMeterService();
      const check = await meter.canGenerateWorksheet(userId);
      
      if (!check.allowed) {
        const ipAddress = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
        
        // Log quota exceeded
        await getAuditLogger().logQuotaExceeded(
          userId,
          userEmail || 'unknown',
          'worksheets',
          check.usage?.worksheets || 0,
          check.limits?.maxWorksheetsPerMonth || 0,
          ipAddress
        );
        
        return NextResponse.json(
          { error: check.reason || 'Quota exceeded' },
          { status: 429 } // 429 Too Many Requests
        );
      }
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Query pages that match criteria
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
      .overlaps('topics', topics)  // Array overlap - matches any topic
      .limit(limit);

    // Apply year filter
    if (yearStart) {
      query = query.gte('papers.year', yearStart);
    }
    if (yearEnd) {
      query = query.lte('papers.year', yearEnd);
    }

    // Apply difficulty filter
    if (difficulty) {
      query = query.eq('difficulty', difficulty);
    }

    // Order by year and season
    query = query.order('papers(year)', { ascending: true });

    const { data: pages, error } = await query;

    if (error) {
      console.error('Query error:', error);
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

    // Get subject_id from first page
    const firstPage = pages[0] as unknown as PageData;
    const subjectId = firstPage.papers.subject_id;

    // Create worksheet record
    const { data: worksheet, error: worksheetError } = await supabase
      .from('worksheets')
      .insert({
        subject_id: subjectId,
        topics,
        year_start: yearStart,
        year_end: yearEnd,
        difficulty,
        total_questions: finalPages.length,
        total_pages: finalPages.length,
        user_id: userId // Add user_id if authenticated
      })
      .select()
      .single();

    if (worksheetError) {
      console.error('Worksheet creation error:', worksheetError);
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
      console.error('Worksheet items error:', itemsError);
    }

    // Track usage (Phase 1)
    if (userId) {
      const meter = getUsageMeterService();
      await meter.incrementUsage(
        userId,
        1, // 1 worksheet
        finalPages.length, // pages
        finalPages.length // questions (assuming 1 question per page)
      );

      // Log worksheet generation
      const ipAddress = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
      await getAuditLogger().logWorksheetGenerated(
        userId,
        userEmail || 'unknown',
        worksheet.id,
        {
          subjectCode: firstPage.papers.subjects.code || 'unknown',
          topics,
          questionsCount: finalPages.length,
          pagesCount: finalPages.length
        },
        ipAddress
      );
    }

    // Format response
    const formattedPages = finalPages.map((page) => ({
      id: page.id,
      questionNumber: page.question_number,
      topics: page.topics,
      difficulty: page.difficulty,
      qpPageUrl: page.qp_page_url,
      msPageUrl: page.ms_page_url,
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
    console.error('API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
