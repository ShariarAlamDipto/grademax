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

  for (const url of pdfUrls) {
    try {
      const pdfBytes = await downloadPDF(url);
      const pdf = await PDFDocument.load(pdfBytes);
      const copiedPages = await mergedPdf.copyPages(pdf, pdf.getPageIndices());
      copiedPages.forEach((page) => mergedPdf.addPage(page));
    } catch (error) {
      console.error(`Error processing PDF ${url}:`, error);
      // Continue with other PDFs
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
    
    // Build full URLs for PDFs
    const storageBase = `${supabaseUrl}/storage/v1/object/public/question-pdfs`;
    
    let pdfUrls: string[];
    if (type === 'markscheme') {
      pdfUrls = items
        .map(item => item.pages.ms_page_url)
        .filter(Boolean)
        .map(url => `${storageBase}/${url}`);
    } else {
      pdfUrls = items
        .map(item => item.pages.qp_page_url)
        .map(url => `${storageBase}/${url}`);
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
    return new Response(mergedPdfBytes, {
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
