import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { PDFDocument } from 'pdf-lib';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

interface WorksheetItem {
  sequence: number;
  pages: {
    qp_page_url: string;
    ms_page_url: string | null;
  };
}

interface WorksheetData {
  id: string;
  topics: string[];
  worksheet_items: WorksheetItem[];
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

  // Download all PDFs in parallel (batches of 10 to avoid overwhelming)
  const batchSize = 10;
  const pdfBytesArray: (ArrayBuffer | null)[] = [];
  
  for (let i = 0; i < pdfUrls.length; i += batchSize) {
    const batch = pdfUrls.slice(i, i + batchSize);
    const results = await Promise.allSettled(batch.map(url => downloadPDF(url)));
    for (const result of results) {
      pdfBytesArray.push(result.status === 'fulfilled' ? result.value : null);
    }
  }

  // Merge in order
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

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id: worksheetId } = await context.params;
    const url = new URL(request.url);
    const type = url.searchParams.get('type') || 'worksheet'; // 'worksheet' or 'markscheme'

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get worksheet with all pages
    const { data: worksheet, error: worksheetError } = await supabase
      .from('worksheets')
      .select(`
        id,
        topics,
        worksheet_items (
          sequence,
          pages (
            qp_page_url,
            ms_page_url
          )
        )
      `)
      .eq('id', worksheetId)
      .single();

    if (worksheetError || !worksheet) {
      return NextResponse.json(
        { error: 'Worksheet not found' },
        { status: 404 }
      );
    }

    // Extract page URLs in sequence order
    const worksheetData = worksheet as unknown as WorksheetData;
    const items = worksheetData.worksheet_items.sort((a, b) => a.sequence - b.sequence);
    
    // Get PDF URLs (they're already full URLs from the database)
    let pdfUrls: string[];
    if (type === 'markscheme') {
      pdfUrls = items
        .map(item => item.pages.ms_page_url)
        .filter(Boolean) as string[];
    } else {
      pdfUrls = items
        .map(item => item.pages.qp_page_url)
        .filter(Boolean) as string[];
    }

    if (pdfUrls.length === 0) {
      return NextResponse.json(
        { error: 'No PDFs found' },
        { status: 404 }
      );
    }

    // Merge PDFs using pdf-lib
    const mergedPdfBytes = await mergePDFs(pdfUrls);

    // Return the merged PDF
    return new Response(mergedPdfBytes as unknown as BodyInit, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${type}-${worksheetId}.pdf"`,
      },
    });

  } catch (error: unknown) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate PDF' },
      { status: 500 }
    );
  }
}
