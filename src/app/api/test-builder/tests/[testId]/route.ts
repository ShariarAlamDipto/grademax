import { NextResponse } from 'next/server';
import { requireAuth } from '@/lib/apiAuth';

interface UpdateTestBody {
  title?: string;
  items?: { pageId: string; sequenceOrder: number }[];
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const { testId } = await context.params;

    const { data: test, error } = await auth.db
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
      .eq('user_id', auth.user.id)
      .single();

    if (error || !test) {
      return NextResponse.json({ error: 'Test not found' }, { status: 404 });
    }

    return NextResponse.json({ test });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const { testId } = await context.params;
    const body: UpdateTestBody = await request.json();

    // Verify ownership before any mutation
    const { data: existing } = await auth.db
      .from('tests')
      .select('id')
      .eq('id', testId)
      .eq('user_id', auth.user.id)
      .single();

    if (!existing) {
      return NextResponse.json({ error: 'Test not found' }, { status: 404 });
    }

    if (body.title !== undefined) {
      const { error } = await auth.db
        .from('tests')
        .update({ title: body.title, updated_at: new Date().toISOString() })
        .eq('id', testId)
        .eq('user_id', auth.user.id);

      if (error) {
        return NextResponse.json(
          { error: 'Failed to update test title', details: error.message },
          { status: 500 }
        );
      }
    }

    if (body.items) {
      const { error: deleteError } = await auth.db
        .from('test_items')
        .delete()
        .eq('test_id', testId);

      if (deleteError) {
        return NextResponse.json(
          { error: 'Failed to update test items', details: deleteError.message },
          { status: 500 }
        );
      }

      if (body.items.length > 0) {
        const testItems = body.items.map((item) => ({
          test_id: testId,
          page_id: item.pageId,
          sequence_order: item.sequenceOrder,
        }));

        const { error: insertError } = await auth.db
          .from('test_items')
          .insert(testItems);

        if (insertError) {
          return NextResponse.json(
            { error: 'Failed to insert new test items', details: insertError.message },
            { status: 500 }
          );
        }
      }

      await auth.db
        .from('tests')
        .update({
          total_questions: body.items.length,
          updated_at: new Date().toISOString(),
        })
        .eq('id', testId)
        .eq('user_id', auth.user.id);
    }

    return NextResponse.json({ success: true });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const { testId } = await context.params;

    const { error } = await auth.db
      .from('tests')
      .delete()
      .eq('id', testId)
      .eq('user_id', auth.user.id);

    if (error) {
      return NextResponse.json(
        { error: 'Failed to delete test', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
