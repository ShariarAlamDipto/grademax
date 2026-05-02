import { NextResponse } from 'next/server';
import type { SupabaseClient } from '@supabase/supabase-js';
import { requireAuth } from '@/lib/apiAuth';
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

interface QuestionRow {
  id: string;
  paper_id: string;
  question_number: string;
  difficulty: string | null;
  page_pdf_url: string | null;
  ms_pdf_url: string | null;
  has_diagram: boolean | null;
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

type AuthSupabase = SupabaseClient;

export async function POST(request: Request) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const supabase = auth.supabase as AuthSupabase;
    const body: GenerateRequest = await request.json();
    const {
      subjectId,
      topics: rawTopics,
      yearStart,
      yearEnd,
      difficulty,
      limit: rawLimit = 50,
      shuffle = false,
    } = body;

    const limit = Math.max(1, Number(rawLimit) || 50);

    if (!rawTopics || rawTopics.length === 0) {
      return NextResponse.json({ error: 'Topics are required' }, { status: 400 });
    }

    const topics = normalizeTopicCodes(rawTopics);

    const { matchingPapers, error: paperError } = await fetchMatchingPapers(
      supabase,
      subjectId,
      yearStart,
      yearEnd,
    );

    if (paperError) {
      return paperError;
    }

    const paperIds = matchingPapers.map((paper) => paper.id);
    const resolvedSubjectId = subjectId || matchingPapers[0]?.subject_id || null;

    if (!resolvedSubjectId) {
      return NextResponse.json({ error: 'Could not determine subject' }, { status: 500 });
    }

    const { data: questionRows, error: questionError } = await supabase
      .from('questions')
      .select(`
        id,
        paper_id,
        question_number,
        difficulty,
        page_pdf_url,
        ms_pdf_url,
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
      .in('paper_id', paperIds)
      .limit(Math.max(limit * 10, limit));

    if (questionError) {
      return NextResponse.json({ error: questionError.message }, { status: 500 });
    }

    const questionIds = (questionRows ?? []).map((question) => question.id);
    const { data: tagRows, error: tagError } = await supabase
      .from('question_tags')
      .select('question_id, topic')
      .in('question_id', questionIds);

    if (tagError) {
      return NextResponse.json({ error: tagError.message }, { status: 500 });
    }

    const topicMap = new Map<string, string[]>();
    for (const row of tagRows ?? []) {
      if (!topicMap.has(row.question_id)) {
        topicMap.set(row.question_id, []);
      }
      if (topics.includes(row.topic)) {
        topicMap.get(row.question_id)?.push(row.topic);
      }
    }

    let finalQuestions = (questionRows ?? [])
      .map((question) => ({
        ...question,
        topics: topicMap.get(question.id) ?? [],
      }))
      .filter((question) => question.topics.length > 0) as unknown as Array<QuestionRow & { topics: string[] }>;

    if (difficulty) {
      finalQuestions = finalQuestions.filter((question) => question.difficulty === difficulty);
    }

    if (shuffle) {
      finalQuestions = [...finalQuestions].sort(() => Math.random() - 0.5);
    }

    finalQuestions = finalQuestions.slice(0, limit);

    if (finalQuestions.length === 0) {
      return NextResponse.json(
        { error: 'No questions found for the selected topics. Try selecting different topics or a wider year range.' },
        { status: 404 }
      );
    }

    const { data: subjectRow } = await supabase
      .from('subjects')
      .select('name')
      .eq('id', resolvedSubjectId)
      .single();

    const worksheetPayload = {
      user_id: auth.user.id,
      title: `${subjectRow?.name ?? 'Worksheet'} Worksheet`,
      description: topics.length > 0 ? `Topics: ${topics.join(', ')}` : null,
      params: {
        subjectId: resolvedSubjectId,
        topics,
        yearStart: yearStart ?? null,
        yearEnd: yearEnd ?? null,
        difficulty: difficulty ?? null,
        limit,
        shuffle,
      },
    };

    const { data: worksheet, error: worksheetError } = await supabase
      .from('worksheets')
      .insert(worksheetPayload)
      .select('id')
      .single();

    if (worksheetError || !worksheet) {
      return NextResponse.json(
        { error: worksheetError?.message || 'Failed to create worksheet' },
        { status: 500 }
      );
    }

    const worksheetItems = finalQuestions.map((question, index) => ({
      worksheet_id: worksheet.id,
      question_id: question.id,
      position: index + 1,
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

    trackUsage({
      user_id: auth.user.id,
      feature: 'worksheet_generate',
      subject_id: resolvedSubjectId,
      subject_name: subjectRow?.name ?? null,
      metadata: { total_questions: finalQuestions.length, topics },
    });

    const formattedPages = finalQuestions.map((question) => ({
      id: question.id,
      questionNumber: question.question_number,
      topics: question.topics,
      difficulty: question.difficulty ?? 'unknown',
      qpPageUrl: toAbsolutePdfUrl(question.page_pdf_url)!,
      msPageUrl: toAbsolutePdfUrl(question.ms_pdf_url),
      hasDiagram: question.has_diagram ?? false,
      year: question.papers?.year,
      season: question.papers?.season,
      paper: question.papers?.paper_number,
    }));

    return NextResponse.json({
      worksheet_id: worksheet.id,
      pages: formattedPages,
      total_questions: formattedPages.length,
      filters: {
        topics,
        yearStart,
        yearEnd,
        difficulty,
      },
    });
  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

async function fetchMatchingPapers(
  supabase: AuthSupabase,
  subjectId: string | undefined,
  yearStart: number | undefined,
  yearEnd: number | undefined,
): Promise<{ matchingPapers: Array<{ id: string; subject_id: string }>; error: null } | { matchingPapers: []; error: NextResponse }> {
  let paperQuery = supabase
    .from('papers')
    .select('id, subject_id');

  if (subjectId) {
    paperQuery = paperQuery.eq('subject_id', subjectId);
  }

  if (yearStart) {
    paperQuery = paperQuery.gte('year', yearStart);
  }

  if (yearEnd) {
    paperQuery = paperQuery.lte('year', yearEnd);
  }

  const { data: matchingPapers, error: paperError } = await paperQuery;

  if (paperError) {
    return {
      matchingPapers: [],
      error: NextResponse.json(
        { error: 'Failed to fetch papers', details: paperError.message },
        { status: 500 }
      ),
    };
  }

  if (!matchingPapers || matchingPapers.length === 0) {
    return {
      matchingPapers: [],
      error: NextResponse.json(
        { error: 'No papers found matching the criteria' },
        { status: 404 }
      ),
    };
  }

  return {
    matchingPapers: matchingPapers as Array<{ id: string; subject_id: string }>,
    error: null,
  };
}