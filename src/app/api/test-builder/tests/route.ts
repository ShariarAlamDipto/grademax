import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * GET /api/test-builder/tests
 * List all tests (optionally filter by subject)
 * 
 * POST /api/test-builder/tests
 * Create a new test with selected questions
 */
export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const subjectId = url.searchParams.get('subjectId');

    const supabase = createClient(supabaseUrl, supabaseKey);

    let query = supabase
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
    console.error('Test builder list API error:', error);
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
}

export async function POST(request: Request) {
  try {
    const body: CreateTestBody = await request.json();
    const { title, subjectId, items } = body;

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

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Create the test
    const { data: test, error: testError } = await supabase
      .from('tests')
      .insert({
        title: title || 'Untitled Test',
        subject_id: subjectId,
        total_questions: items.length,
        total_marks: 0,
        status: 'draft',
      })
      .select()
      .single();

    if (testError) {
      return NextResponse.json(
        { error: 'Failed to create test', details: testError.message },
        { status: 500 }
      );
    }

    // Insert test items
    const testItems = items.map((item) => ({
      test_id: test.id,
      page_id: item.pageId,
      sequence_order: item.sequenceOrder,
    }));

    const { error: itemsError } = await supabase
      .from('test_items')
      .insert(testItems);

    if (itemsError) {
      // Clean up the test on failure
      await supabase.from('tests').delete().eq('id', test.id);
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
        status: test.status,
      }
    }, { status: 201 });

  } catch (error: unknown) {
    console.error('Test builder create API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
