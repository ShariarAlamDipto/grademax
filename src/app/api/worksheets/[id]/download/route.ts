import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';

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
  year_start: number | null;
  year_end: number | null;
  difficulty: string | null;
  worksheet_items: WorksheetItem[];
  subjects: { name: string; level: string } | null;
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

async function buildCoverPage(
  doc: PDFDocument,
  opts: {
    type: 'worksheet' | 'markscheme';
    subjectName: string;
    level: string;
    topics: string[];
    yearStart: number | null;
    yearEnd: number | null;
    difficulty: string | null;
    totalQuestions: number;
  }
) {
  const page = doc.addPage(PageSizes.A4);
  const { width, height } = page.getSize();
  const bold = await doc.embedFont(StandardFonts.TimesRomanBold);
  const regular = await doc.embedFont(StandardFonts.TimesRoman);
  const black = rgb(0, 0, 0);
  const gray = rgb(0.4, 0.4, 0.4);

  // "GradeMax Worksheets" header — sized to 70% of page width
  const headerText = 'GradeMax Worksheets';
  const targetW = width * 0.70;
  const headerSize = targetW / bold.widthOfTextAtSize(headerText, 1);
  const headerW = bold.widthOfTextAtSize(headerText, headerSize);
  page.drawText(headerText, {
    x: (width - headerW) / 2,
    y: height - 160,
    size: headerSize,
    font: bold,
    color: black,
  });

  // Type label
  const typeLabel = opts.type === 'markscheme' ? 'MARK SCHEME' : 'WORKSHEET';
  const labelW = bold.widthOfTextAtSize(typeLabel, 11);
  page.drawText(typeLabel, {
    x: (width - labelW) / 2,
    y: height - 210,
    size: 11,
    font: bold,
    color: gray,
  });

  // Subject title
  const titleText = opts.subjectName || 'Worksheet';
  const titleSize = titleText.length > 30 ? 22 : 28;
  const titleW = bold.widthOfTextAtSize(titleText, titleSize);
  page.drawText(titleText, {
    x: (width - titleW) / 2,
    y: height - 260,
    size: titleSize,
    font: bold,
    color: black,
  });

  // Subject / level line
  const subjectLine = [opts.subjectName, opts.level].filter(Boolean).join('  ·  ');
  if (subjectLine) {
    const subW = regular.widthOfTextAtSize(subjectLine, 12);
    page.drawText(subjectLine, {
      x: (width - subW) / 2,
      y: height - 285,
      size: 12,
      font: regular,
      color: gray,
    });
  }

  // Thin rule
  const ruleW = 260;
  page.drawRectangle({
    x: (width - ruleW) / 2,
    y: height - 315,
    width: ruleW,
    height: 0.5,
    color: rgb(0.7, 0.7, 0.7),
  });

  // Fields
  const fieldStartY = height - 375;
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
      page.drawRectangle({ x: lineStartX, y: y - 2, width: lineEndX - lineStartX, height: 0.5, color: rgb(0.6, 0.6, 0.6) });
    }
  };

  drawField('Name:', null, fieldStartY);
  drawField('Total Questions:', String(opts.totalQuestions), fieldStartY - fieldGap);
  drawField('Marks Received:', null, fieldStartY - fieldGap * 2);

  // Topics line
  if (opts.topics.length > 0) {
    const topicsText = `Topics: ${opts.topics.slice(0, 6).join(', ')}${opts.topics.length > 6 ? ` +${opts.topics.length - 6} more` : ''}`;
    const topicsW = regular.widthOfTextAtSize(topicsText, 10);
    page.drawText(topicsText, {
      x: (width - topicsW) / 2,
      y: fieldStartY - fieldGap * 3 - 10,
      size: 10,
      font: regular,
      color: gray,
    });
  }

  // Year range / difficulty filter note
  const filterParts: string[] = [];
  if (opts.yearStart || opts.yearEnd) {
    filterParts.push(`Years: ${opts.yearStart ?? ''}–${opts.yearEnd ?? ''}`);
  }
  if (opts.difficulty) {
    filterParts.push(`Difficulty: ${opts.difficulty}`);
  }
  if (filterParts.length > 0) {
    const filterText = filterParts.join('  ·  ');
    const filterW = regular.widthOfTextAtSize(filterText, 9);
    page.drawText(filterText, {
      x: (width - filterW) / 2,
      y: fieldStartY - fieldGap * 3 - 28,
      size: 9,
      font: regular,
      color: gray,
    });
  }

  // Bottom branding
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

async function mergePDFs(
  pdfUrls: string[],
  coverOpts: Parameters<typeof buildCoverPage>[1]
): Promise<Uint8Array> {
  const mergedPdf = await PDFDocument.create();

  await buildCoverPage(mergedPdf, coverOpts);

  const [a4W, a4H] = PageSizes.A4;
  const batchSize = 10;

  for (let i = 0; i < pdfUrls.length; i += batchSize) {
    const batch = pdfUrls.slice(i, i + batchSize);
    const results = await Promise.allSettled(batch.map(url => downloadPDF(url)));
    for (const result of results) {
      if (result.status !== 'fulfilled' || !result.value) continue;
      try {
        const srcPdf = await PDFDocument.load(result.value);
        for (const pi of srcPdf.getPageIndices()) {
          const srcPage = srcPdf.getPage(pi);
          const { width: srcW, height: srcH } = srcPage.getSize();
          if (Math.abs(srcW - a4W) < 2 && Math.abs(srcH - a4H) < 2) {
            const [copied] = await mergedPdf.copyPages(srcPdf, [pi]);
            mergedPdf.addPage(copied);
          } else {
            const [embedded] = await mergedPdf.embedPdf(srcPdf, [pi]);
            const a4Page = mergedPdf.addPage(PageSizes.A4);
            const scale = Math.min(a4W / srcW, a4H / srcH, 1);
            a4Page.drawPage(embedded, {
              x: (a4W - srcW * scale) / 2,
              y: (a4H - srcH * scale) / 2,
              width: srcW * scale,
              height: srcH * scale,
            });
          }
        }
      } catch (error) {
        console.error('Error merging PDF page:', error);
      }
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

    // Get worksheet with all pages and subject info
    const { data: worksheet, error: worksheetError } = await supabase
      .from('worksheets')
      .select(`
        id,
        topics,
        year_start,
        year_end,
        difficulty,
        total_questions,
        worksheet_items (
          sequence,
          pages (
            qp_page_url,
            ms_page_url
          )
        ),
        subjects (
          name,
          level
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

    // Merge PDFs with cover page
    const coverOpts = {
      type: type as 'worksheet' | 'markscheme',
      subjectName: worksheetData.subjects?.name ?? '',
      level: worksheetData.subjects?.level ?? '',
      topics: worksheetData.topics ?? [],
      yearStart: worksheetData.year_start,
      yearEnd: worksheetData.year_end,
      difficulty: worksheetData.difficulty,
      totalQuestions: items.length,
    };
    const mergedPdfBytes = await mergePDFs(pdfUrls, coverOpts);

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
