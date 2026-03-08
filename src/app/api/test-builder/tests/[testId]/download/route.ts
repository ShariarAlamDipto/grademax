import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { PDFDocument } from 'pdf-lib';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

interface TestItemRow {
  sequence_order: number;
  pages: {
    qp_page_url: string;
    ms_page_url: string | null;
  };
}

interface TestRow {
  id: string;
  title: string;
  test_items: TestItemRow[];
}

async function downloadPDF(url: string): Promise<ArrayBuffer> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download PDF from ${url}`);
  }
  return await response.arrayBuffer();
}

async function mergePDFs(pdfUrls: string[]): Promise<Uint8Array> {
  const mergedPdf = await PDFDocument.create();

  const batchSize = 10;
  const pdfBytesArray: (ArrayBuffer | null)[] = [];

  for (let i = 0; i < pdfUrls.length; i += batchSize) {
    const batch = pdfUrls.slice(i, i + batchSize);
    const results = await Promise.allSettled(batch.map(url => downloadPDF(url)));
    for (const result of results) {
      pdfBytesArray.push(result.status === 'fulfilled' ? result.value : null);
    }
  }

  for (const pdfBytes of pdfBytesArray) {
    if (!pdfBytes) continue;
    try {
      const pdf = await PDFDocument.load(pdfBytes);
      const copiedPages = await mergedPdf.copyPages(pdf, pdf.getPageIndices());
      copiedPages.forEach((page) => mergedPdf.addPage(page));
    } catch (error) {
      console.error('Error merging PDF page:', error);
    }
  }

  return await mergedPdf.save();
}

/**
 * GET /api/test-builder/tests/[testId]/download?type=worksheet|markscheme
 * 
 * Generate and download the merged PDF for a test.
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ testId: string }> }
) {
  try {
    const { testId } = await context.params;
    const url = new URL(request.url);
    const type = url.searchParams.get('type') || 'worksheet';

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get test with items and page URLs
    const { data: test, error: testError } = await supabase
      .from('tests')
      .select(`
        id,
        title,
        test_items (
          sequence_order,
          pages (
            qp_page_url,
            ms_page_url
          )
        )
      `)
      .eq('id', testId)
      .single();

    if (testError || !test) {
      return NextResponse.json(
        { error: 'Test not found' },
        { status: 404 }
      );
    }

    const testData = test as unknown as TestRow;
    const items = testData.test_items.sort((a, b) => a.sequence_order - b.sequence_order);

    // Extract PDF URLs based on type
    let pdfUrls: string[];
    if (type === 'markscheme') {
      pdfUrls = items
        .map(item => item.pages?.ms_page_url)
        .filter(Boolean) as string[];
    } else {
      pdfUrls = items
        .map(item => item.pages?.qp_page_url)
        .filter(Boolean) as string[];
    }

    if (pdfUrls.length === 0) {
      return NextResponse.json(
        { error: `No ${type} PDFs found for this test` },
        { status: 404 }
      );
    }

    // Merge all PDFs
    const mergedPdfBytes = await mergePDFs(pdfUrls);

    const filename = `${testData.title.replace(/[^a-zA-Z0-9]/g, '_')}_${type}.pdf`;

    return new Response(mergedPdfBytes as unknown as BodyInit, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${filename}"`,
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
