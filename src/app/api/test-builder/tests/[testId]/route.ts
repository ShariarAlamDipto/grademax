import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * GET /api/test-builder/tests/[testId]
 * Get a single test with its items
 * 
 * PUT /api/test-builder/tests/[testId]
 * Update a test (reorder items, change title)
 * 
 * DELETE /api/test-builder/tests/[testId]
 * Delete a test
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const { testId } = await context.params;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data: test, error } = await supabase
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
        ),
        test_items (
          id,
          page_id,
          sequence_order,
          pages (
            id,
            question_number,
            topics,
            difficulty,
            qp_page_url,
            ms_page_url,
            has_diagram,
            text_excerpt,
            papers (
              year,
              season,
              paper_number
            )
          )
        )
      `)
      .eq('id', testId)
      .single();

    if (error || !test) {
      return NextResponse.json(
        { error: 'Test not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({ test });

  } catch (error: unknown) {
    console.error('Test builder get API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

interface UpdateTestBody {
  title?: string;
  items?: { pageId: string; sequenceOrder: number }[];
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const { testId } = await context.params;
    const body: UpdateTestBody = await request.json();
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Update title if provided
    if (body.title !== undefined) {
      const { error } = await supabase
        .from('tests')
        .update({ title: body.title, updated_at: new Date().toISOString() })
        .eq('id', testId);

      if (error) {
        return NextResponse.json(
          { error: 'Failed to update test title', details: error.message },
          { status: 500 }
        );
      }
    }

    // Replace items if provided (delete all, re-insert)
    if (body.items) {
      // Delete existing items
      const { error: deleteError } = await supabase
        .from('test_items')
        .delete()
        .eq('test_id', testId);

      if (deleteError) {
        return NextResponse.json(
          { error: 'Failed to update test items', details: deleteError.message },
          { status: 500 }
        );
      }

      // Insert new items
      if (body.items.length > 0) {
        const testItems = body.items.map((item) => ({
          test_id: testId,
          page_id: item.pageId,
          sequence_order: item.sequenceOrder,
        }));

        const { error: insertError } = await supabase
          .from('test_items')
          .insert(testItems);

        if (insertError) {
          return NextResponse.json(
            { error: 'Failed to insert new test items', details: insertError.message },
            { status: 500 }
          );
        }
      }

      // Update cached count
      await supabase
        .from('tests')
        .update({
          total_questions: body.items.length,
          updated_at: new Date().toISOString(),
        })
        .eq('id', testId);
    }

    return NextResponse.json({ success: true });

  } catch (error: unknown) {
    console.error('Test builder update API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const { testId } = await context.params;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // CASCADE will delete test_items too
    const { error } = await supabase
      .from('tests')
      .delete()
      .eq('id', testId);

    if (error) {
      return NextResponse.json(
        { error: 'Failed to delete test', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });

  } catch (error: unknown) {
    console.error('Test builder delete API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
