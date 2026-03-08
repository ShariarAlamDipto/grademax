import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
// Prefer service role key for server-side operations (bypasses RLS), fallback to anon
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

async function downloadPDF(url: string): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
    if (!response.ok) return null;
    return await response.arrayBuffer();
  } catch {
    return null;
  }
}

/**
 * Build a minimalistic, centered cover page with Times New Roman.
 * Just: title, name field, total marks, marks received.
 */
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
  const gray = rgb(0.4, 0.4, 0.4);

  // ── Centered label at top ──
  const typeLabel = opts.type === 'markscheme' ? 'MARK SCHEME' : 'QUESTION PAPER';
  const labelW = bold.widthOfTextAtSize(typeLabel, 11);
  page.drawText(typeLabel, {
    x: (width - labelW) / 2,
    y: height - 200,
    size: 11,
    font: bold,
    color: gray,
  });

  // ── Title ──
  const displayTitle = opts.title || 'Untitled Test';
  const titleSize = displayTitle.length > 30 ? 22 : 28;
  const titleW = bold.widthOfTextAtSize(displayTitle, titleSize);
  page.drawText(displayTitle, {
    x: (width - titleW) / 2,
    y: height - 250,
    size: titleSize,
    font: bold,
    color: black,
  });

  // ── Subject line ──
  const subjectLine = [opts.subjectName, opts.level].filter(Boolean).join('  ·  ');
  if (subjectLine) {
    const subW = regular.widthOfTextAtSize(subjectLine, 12);
    page.drawText(subjectLine, {
      x: (width - subW) / 2,
      y: height - 280,
      size: 12,
      font: regular,
      color: gray,
    });
  }

  // ── Thin rule ──
  const ruleW = 260;
  page.drawRectangle({
    x: (width - ruleW) / 2,
    y: height - 310,
    width: ruleW,
    height: 0.5,
    color: rgb(0.7, 0.7, 0.7),
  });

  // ── Fields: Name, Total Marks, Marks Received ──
  const fieldStartY = height - 370;
  const fieldGap = 45;
  const labelX = (width - ruleW) / 2;
  const lineStartX = labelX + 130;
  const lineEndX = labelX + ruleW;

  const drawField = (label: string, value: string | null, y: number) => {
    page.drawText(label, { x: labelX, y, size: 13, font: regular, color: black });
    if (value) {
      const vw = bold.widthOfTextAtSize(value, 13);
      page.drawText(value, { x: lineEndX - vw, y, size: 13, font: bold, color: black });
    } else {
      // Draw underline for fill-in
      page.drawRectangle({ x: lineStartX, y: y - 2, width: lineEndX - lineStartX, height: 0.5, color: rgb(0.6, 0.6, 0.6) });
    }
  };

  drawField('Name:', null, fieldStartY);
  drawField('Total Marks:', String(opts.totalMarks), fieldStartY - fieldGap);
  drawField('Marks Received:', null, fieldStartY - fieldGap * 2);

  // ── Bottom branding ──
  const brand = 'GradeMax';
  const brandW = regular.widthOfTextAtSize(brand, 9);
  page.drawText(brand, {
    x: (width - brandW) / 2,
    y: 40,
    size: 9,
    font: regular,
    color: rgb(0.7, 0.7, 0.7),
  });
}

/**
 * GET /api/test-builder/tests/[testId]/download?type=worksheet|markscheme
 */
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
      console.error('[download] Test query error:', testError?.message, 'testId:', testId);
      return NextResponse.json({ error: 'Test not found', details: testError?.message }, { status: 404 });
    }

    const testData = test as unknown as TestRow;
    const items = testData.test_items.sort((a, b) => a.sequence_order - b.sequence_order);

    console.log(`[download] Test "${testData.title}" has ${items.length} items, type=${type}`);

    const pdfUrls = items
      .map(item => type === 'markscheme' ? item.pages?.ms_page_url : item.pages?.qp_page_url)
      .filter(Boolean) as string[];

    if (pdfUrls.length === 0) {
      console.error('[download] No PDF URLs found. Items:', JSON.stringify(items.map(i => ({
        seq: i.sequence_order,
        qp: i.pages?.qp_page_url?.slice(0, 60),
        ms: i.pages?.ms_page_url?.slice(0, 60),
      }))));
      return NextResponse.json({ error: `No ${type} PDFs found for this test` }, { status: 404 });
    }

    console.log(`[download] Merging ${pdfUrls.length} PDFs...`);

    // Create merged PDF with cover page
    const mergedPdf = await PDFDocument.create();

    await buildCoverPage(mergedPdf, {
      title: testData.title,
      subjectName: testData.subjects?.name || '',
      subjectCode: testData.subjects?.code || '',
      level: testData.subjects?.level || '',
      totalQuestions: testData.total_questions || items.length,
      totalMarks: items.length * 4,
      type,
    });

    // Download and merge PDFs in parallel batches — embed into A4 pages
    const [a4W, a4H] = PageSizes.A4;
    let successCount = 0;
    const batchSize = 10;
    for (let i = 0; i < pdfUrls.length; i += batchSize) {
      const batch = pdfUrls.slice(i, i + batchSize);
      const results = await Promise.allSettled(batch.map(u => downloadPDF(u)));
      for (let j = 0; j < results.length; j++) {
        const result = results[j];
        if (result.status !== 'fulfilled' || !result.value) {
          console.warn(`[download] Failed to download PDF ${i + j + 1}:`, batch[j]?.slice(0, 80));
          continue;
        }
        try {
          const srcPdf = await PDFDocument.load(result.value);
          const pageIndices = srcPdf.getPageIndices();
          for (const pi of pageIndices) {
            const srcPage = srcPdf.getPage(pi);
            const { width: srcW, height: srcH } = srcPage.getSize();
            // If already A4 (within 2pt tolerance), copy directly for quality
            if (Math.abs(srcW - a4W) < 2 && Math.abs(srcH - a4H) < 2) {
              const [copied] = await mergedPdf.copyPages(srcPdf, [pi]);
              mergedPdf.addPage(copied);
            } else {
              // Embed into an A4 frame, scaled to fit, centered
              const [embedded] = await mergedPdf.embedPdf(srcPdf, [pi]);
              const a4Page = mergedPdf.addPage(PageSizes.A4);
              const scale = Math.min(a4W / srcW, a4H / srcH, 1);
              const scaledW = srcW * scale;
              const scaledH = srcH * scale;
              a4Page.drawPage(embedded, {
                x: (a4W - scaledW) / 2,
                y: (a4H - scaledH) / 2,
                width: scaledW,
                height: scaledH,
              });
            }
          }
          successCount++;
        } catch (err) {
          console.error(`[download] Error merging PDF ${i + j + 1}:`, err);
        }
      }
    }

    console.log(`[download] Merged ${successCount}/${pdfUrls.length} PDFs successfully`);

    if (successCount === 0) {
      return NextResponse.json({ error: 'Could not download any question PDFs. Please try again.' }, { status: 500 });
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
    console.error('Test builder download API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate PDF' },
      { status: 500 }
    );
  }
}
