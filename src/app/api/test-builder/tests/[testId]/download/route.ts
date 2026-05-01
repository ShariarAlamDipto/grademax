import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';
import { mergePagePdfs, toAbsolutePdfUrl } from '@/lib/pdfUtils';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

interface TestItemRow {
  sequence_order: number;
  pages: {
    qp_page_url: string;
    ms_page_url: string | null;
    question_number: string | null;
  };
}

interface TestRow {
  id: string;
  title: string;
  subject_id: string;
  total_questions: number;
  test_items: TestItemRow[];
  subjects: { name: string; code: string; level: string } | null;
}

async function buildCoverPage(
  doc: PDFDocument,
  opts: {
    title: string;
    subjectName: string;
    subjectCode: string;
    level: string;
    totalQuestions: number;
    totalMarks: number;
    type: 'worksheet' | 'markscheme';
  }
) {
  const page = doc.addPage(PageSizes.A4);
  const { width, height } = page.getSize();

  const bold = await doc.embedFont(StandardFonts.TimesRomanBold);
  const regular = await doc.embedFont(StandardFonts.TimesRoman);
  const black = rgb(0, 0, 0);

  const headerText = 'GradeMax Exams';
  const targetW = width * 0.70;
  const headerSize = targetW / bold.widthOfTextAtSize(headerText, 1);
  const headerW = bold.widthOfTextAtSize(headerText, headerSize);
  page.drawText(headerText, {
    x: (width - headerW) / 2,
    y: height - 180,
    size: headerSize,
    font: bold,
    color: black,
  });

  const typeLabel = opts.type === 'markscheme' ? 'MARK SCHEME' : 'QUESTION PAPER';
  const labelW = bold.widthOfTextAtSize(typeLabel, 11);
  page.drawText(typeLabel, {
    x: (width - labelW) / 2,
    y: height - 220,
    size: 11,
    font: bold,
    color: black,
  });

  const displayTitle = opts.title || 'Untitled Test';
  const titleSize = displayTitle.length > 30 ? 22 : 28;
  const titleW = bold.widthOfTextAtSize(displayTitle, titleSize);
  page.drawText(displayTitle, {
    x: (width - titleW) / 2,
    y: height - 270,
    size: titleSize,
    font: bold,
    color: black,
  });

  const subjectLine = [opts.subjectName, opts.level].filter(Boolean).join('  ·  ');
  if (subjectLine) {
    const subW = regular.widthOfTextAtSize(subjectLine, 12);
    page.drawText(subjectLine, {
      x: (width - subW) / 2,
      y: height - 300,
      size: 12,
      font: regular,
      color: black,
    });
  }

  const ruleW = 260;
  page.drawRectangle({
    x: (width - ruleW) / 2,
    y: height - 330,
    width: ruleW,
    height: 0.5,
    color: black,
  });

  const fieldStartY = height - 390;
  const fieldGap = 45;
  const labelX = (width - ruleW) / 2;
  const lineStartX = labelX + 130;
  const lineEndX = labelX + ruleW;

  const drawField = (label: string, y: number) => {
    page.drawText(label, { x: labelX, y, size: 13, font: regular, color: black });
    page.drawRectangle({ x: lineStartX, y: y - 2, width: lineEndX - lineStartX, height: 0.5, color: black });
  };

  drawField('Name:', fieldStartY);
  drawField('Total Marks:', fieldStartY - fieldGap);
  drawField('Marks Received:', fieldStartY - fieldGap * 2);

  const brand = 'GradeMax';
  const brandW = regular.widthOfTextAtSize(brand, 9);
  page.drawText(brand, {
    x: (width - brandW) / 2,
    y: 40,
    size: 9,
    font: regular,
    color: black,
  });
}

export async function GET(
  request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const { testId } = await context.params;
    const url = new URL(request.url);
    const type = (url.searchParams.get('type') || 'worksheet') as 'worksheet' | 'markscheme';

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data: test, error: testError } = await supabase
      .from('tests')
      .select(`
        id,
        title,
        subject_id,
        total_questions,
        test_items (
          sequence_order,
          pages (
            qp_page_url,
            ms_page_url,
            question_number
          )
        ),
        subjects (
          name,
          code,
          level
        )
      `)
      .eq('id', testId)
      .single();

    if (testError || !test) {
      return NextResponse.json(
        { error: 'Test not found', details: testError?.message },
        { status: 404 }
      );
    }

    const testData = test as unknown as TestRow;
    const items = testData.test_items.sort((a, b) => a.sequence_order - b.sequence_order);

    const pdfUrls = items
      .map(item => toAbsolutePdfUrl(type === 'markscheme' ? item.pages?.ms_page_url : item.pages?.qp_page_url))
      .filter(Boolean) as string[];

    if (pdfUrls.length === 0) {
      return NextResponse.json(
        { error: `No ${type} PDFs found for this test` },
        { status: 404 }
      );
    }

    const mergedPdf = await PDFDocument.create();

    await buildCoverPage(mergedPdf, {
      title: testData.title,
      subjectName: testData.subjects?.name || '',
      subjectCode: testData.subjects?.code || '',
      level: testData.subjects?.level || '',
      totalQuestions: testData.total_questions || items.length,
      totalMarks: 0,
      type,
    });

    const successCount = await mergePagePdfs(mergedPdf, pdfUrls);

    if (successCount === 0) {
      return NextResponse.json(
        { error: 'Could not download any question PDFs. Please try again.' },
        { status: 500 }
      );
    }

    const mergedBytes = await mergedPdf.save();
    const filename = `${testData.title.replace(/[^a-zA-Z0-9 ]/g, '').replace(/\s+/g, '_')}_${type}.pdf`;

    return new Response(Buffer.from(mergedBytes), {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Cache-Control': 'no-store',
      },
    });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate PDF' },
      { status: 500 }
    );
  }
}
