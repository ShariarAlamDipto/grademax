import { NextResponse } from 'next/server';
import { requireAuth } from '@/lib/apiAuth';
import { getSupabaseAdmin } from '@/lib/supabaseAdmin';

export async function GET(request: Request) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const url = new URL(request.url);
    const subjectId = url.searchParams.get('subjectId');

    const db = getSupabaseAdmin() || auth.db;

    let query = db
      .from('tests')
      .select(`
        id,
        title,
        subject_id,
        total_marks,
        total_questions,
        status,
        created_at,
        updated_at,
        subjects (
          name,
          code,
          level
        )
      `)
      .order('updated_at', { ascending: false })
      .limit(50);

    if (subjectId) {
      query = query.eq('subject_id', subjectId);
    }

    const { data: tests, error } = await query;

    if (error) {
      return NextResponse.json(
        { error: 'Failed to fetch tests', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ tests: tests || [] });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

interface CreateTestBody {
  title?: string;
  subjectId: string;
  items: { pageId: string; sequenceOrder: number }[];
  totalMarks?: number;
}

export async function POST(request: Request) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const body: CreateTestBody = await request.json();
    const { title, subjectId, items, totalMarks } = body;

    if (!subjectId) {
      return NextResponse.json(
        { error: 'subjectId is required' },
        { status: 400 }
      );
    }

    if (!items || items.length === 0) {
      return NextResponse.json(
        { error: 'At least one question is required' },
        { status: 400 }
      );
    }

    const db = getSupabaseAdmin() || auth.db;

    const { data: test, error: testError } = await db
      .from('tests')
      .insert({
        title: title || 'Untitled Test',
        subject_id: subjectId,
        total_questions: items.length,
        total_marks: typeof totalMarks === 'number' ? totalMarks : items.length,
        status: 'draft',
      })
      .select('id, title, total_marks, total_questions, status')
      .single();

    if (testError) {
      return NextResponse.json(
        { error: 'Failed to create test', details: testError.message },
        { status: 500 }
      );
    }

    const testItems = items.map((item) => ({
      test_id: test.id,
      page_id: item.pageId,
      sequence_order: item.sequenceOrder,
    }));

    const { error: itemsError } = await db
      .from('test_items')
      .insert(testItems);

    if (itemsError) {
      await db.from('tests').delete().eq('id', test.id);
      return NextResponse.json(
        { error: 'Failed to add questions to test', details: itemsError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      test: {
        id: test.id,
        title: test.title,
        totalQuestions: items.length,
        totalMarks: test.total_marks,
        status: test.status,
      }
    }, { status: 201 });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
