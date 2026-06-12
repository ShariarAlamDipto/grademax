import { NextResponse } from 'next/server';
import type { SupabaseClient } from '@supabase/supabase-js';
import { requireAuth } from '@/lib/apiAuth';
import { normalizeTopicCodes } from '@/lib/topicCodes';
import { trackUsage } from '@/lib/trackUsage';
import { toAbsolutePdfUrl } from '@/lib/pdfUtils';

// Several Supabase round-trips happen here. On a cold serverless start over a
// slow mobile connection the default 10 s budget is tight enough that the
// connection can be dropped mid-flight, surfacing as `Failed to fetch` in the
// browser. Bump the budget and pin the runtime.
export const runtime = 'nodejs';
export const maxDuration = 30;
export const dynamic = 'force-dynamic';

interface GenerateRequest {
  subjectId?: string;
  topics: string[];
  yearStart?: number;
  yearEnd?: number;
  difficulty?: string;
  limit?: number;
  shuffle?: boolean;
}

interface PageRow {
  id: string;
  paper_id: string;
  question_number: string;
  difficulty: string | null;
  qp_page_url: string | null;
  ms_page_url: string | null;
  has_diagram: boolean | null;
  topics: string[];
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

function fisherYatesShuffle<T>(items: readonly T[]): T[] {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

/**
 * Stratified selection: groups candidates by primary topic and picks
 * round-robin across the groups so a multi-topic worksheet covers every
 * requested topic instead of clustering on whichever paper sorted first.
 * Within a group, deterministic mode prefers recent years.
 */
function stratifiedSelect(
  candidates: readonly PageRow[],
  requestedTopics: readonly string[],
  limit: number,
  shuffle: boolean,
): PageRow[] {
  const groups = new Map<string, PageRow[]>();
  for (const page of candidates) {
    const primaryTopic =
      page.topics?.find((t) => requestedTopics.includes(t)) ?? page.topics?.[0] ?? '';
    const group = groups.get(primaryTopic);
    if (group) group.push(page);
    else groups.set(primaryTopic, [page]);
  }

  const orderedGroups = [...groups.values()].map((group) =>
    shuffle
      ? fisherYatesShuffle(group)
      : [...group].sort((a, b) => (b.papers?.year ?? 0) - (a.papers?.year ?? 0)),
  );

  const selected: PageRow[] = [];
  for (let round = 0; selected.length < limit; round++) {
    let pickedAny = false;
    for (const group of orderedGroups) {
      if (round < group.length && selected.length < limit) {
        selected.push(group[round]);
        pickedAny = true;
      }
    }
    if (!pickedAny) break;
  }

  return shuffle ? fisherYatesShuffle(selected) : selected;
}

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

    // Query pages directly with topic overlap filter — same approach as the
    // test builder. This ensures rare topics (e.g. Astrophysics) are not
    // cut off by a pre-fetch limit the way the old questions+question_tags
    // two-step query was.
    let pageQuery = supabase
      .from('pages')
      .select(`
        id,
        paper_id,
        question_number,
        difficulty,
        qp_page_url,
        ms_page_url,
        has_diagram,
        topics,
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
      .in('paper_id', paperIds)
      .limit(5000);

    if (topics.length > 0) {
      pageQuery = pageQuery.overlaps('topics', topics);
    }

    if (difficulty) {
      pageQuery = pageQuery.eq('difficulty', difficulty);
    }

    const { data: pageRows, error: pageError } = await pageQuery;

    if (pageError) {
      return NextResponse.json({ error: pageError.message }, { status: 500 });
    }

    const candidates = (pageRows ?? []) as unknown as PageRow[];
    const finalQuestions = stratifiedSelect(candidates, topics, limit, shuffle);

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

    // Best-effort: store page IDs in worksheet_items for history.
    // Non-fatal — a FK mismatch on legacy rows must not block PDF delivery.
    const worksheetItems = finalQuestions.map((page, index) => ({
      worksheet_id: worksheet.id,
      question_id: page.id,
      position: index + 1,
    }));
    await supabase
      .from('worksheet_items')
      .insert(worksheetItems)
      .then(() => undefined, () => undefined);

    trackUsage({
      user_id: auth.user.id,
      feature: 'worksheet_generate',
      subject_id: resolvedSubjectId,
      subject_name: subjectRow?.name ?? null,
      metadata: { total_questions: finalQuestions.length, topics },
    });

    const formattedPages = finalQuestions.map((page) => ({
      id: page.id,
      questionNumber: page.question_number,
      topics: page.topics,
      difficulty: page.difficulty ?? 'unknown',
      qpPageUrl: toAbsolutePdfUrl(page.qp_page_url)!,
      msPageUrl: toAbsolutePdfUrl(page.ms_page_url),
      hasDiagram: page.has_diagram ?? false,
      year: page.papers?.year,
      season: page.papers?.season,
      paper: page.papers?.paper_number,
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
