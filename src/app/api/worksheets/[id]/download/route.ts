import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';
import { mergePagePdfs, toAbsolutePdfUrl } from '@/lib/pdfUtils';

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

  const typeLabel = opts.type === 'markscheme' ? 'MARK SCHEME' : 'WORKSHEET';
  const labelW = bold.widthOfTextAtSize(typeLabel, 11);
  page.drawText(typeLabel, {
    x: (width - labelW) / 2,
    y: height - 210,
    size: 11,
    font: bold,
    color: gray,
  });

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

  const ruleW = 260;
  page.drawRectangle({
    x: (width - ruleW) / 2,
    y: height - 315,
    width: ruleW,
    height: 0.5,
    color: rgb(0.7, 0.7, 0.7),
  });

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

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id: worksheetId } = await context.params;
    const url = new URL(request.url);
    const type = url.searchParams.get('type') || 'worksheet';

    const supabase = createClient(supabaseUrl, supabaseKey);

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

    const worksheetData = worksheet as unknown as WorksheetData;
    const items = worksheetData.worksheet_items.sort((a, b) => a.sequence - b.sequence);

    let pdfUrls: string[];
    if (type === 'markscheme') {
      pdfUrls = items.map(item => toAbsolutePdfUrl(item.pages.ms_page_url)).filter(Boolean) as string[];
    } else {
      pdfUrls = items.map(item => toAbsolutePdfUrl(item.pages.qp_page_url)).filter(Boolean) as string[];
    }

    if (pdfUrls.length === 0) {
      return NextResponse.json({ error: 'No PDFs found' }, { status: 404 });
    }

    const mergedPdf = await PDFDocument.create();

    await buildCoverPage(mergedPdf, {
      type: type as 'worksheet' | 'markscheme',
      subjectName: worksheetData.subjects?.name ?? '',
      level: worksheetData.subjects?.level ?? '',
      topics: worksheetData.topics ?? [],
      yearStart: worksheetData.year_start,
      yearEnd: worksheetData.year_end,
      difficulty: worksheetData.difficulty,
      totalQuestions: items.length,
    });

    const successCount = await mergePagePdfs(mergedPdf, pdfUrls);

    if (successCount === 0) {
      return NextResponse.json(
        { error: 'Could not download any question PDFs. Please try again.' },
        { status: 500 }
      );
    }

    const mergedPdfBytes = await mergedPdf.save();

    return new Response(mergedPdfBytes as unknown as BodyInit, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${type}-${worksheetId}.pdf"`,
      },
    });

  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate PDF' },
      { status: 500 }
    );
  }
}
