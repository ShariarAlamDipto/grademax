import { NextResponse } from 'next/server';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';
import { requireAuth } from '@/lib/apiAuth';
import { mergePagePdfs, toAbsolutePdfUrl } from '@/lib/pdfUtils';

interface WorksheetItem {
  position: number;
  questions: {
    page_pdf_url: string | null;
    ms_pdf_url: string | null;
  } | null;
}

interface WorksheetData {
  id: string;
  title: string | null;
  params: {
    topics?: string[];
    yearStart?: number | null;
    yearEnd?: number | null;
    difficulty?: string | null;
  } | null;
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
    const auth = await requireAuth();
    if ('error' in auth) return auth.error;

    const { id: worksheetId } = await context.params;
    const url = new URL(request.url);
    const type = url.searchParams.get('type') || 'worksheet';
    const supabase = auth.supabase;

    const { data: worksheet, error: worksheetError } = await supabase
      .from('worksheets')
      .select(`
        id,
        title,
        params,
        worksheet_items (
          position,
          questions (
            page_pdf_url,
            ms_pdf_url
          )
        ),
        subjects (
          name,
          level
        )
      `)
      .eq('id', worksheetId)
      .eq('user_id', auth.user.id)
      .single();

    if (worksheetError || !worksheet) {
      return NextResponse.json({ error: 'Worksheet not found' }, { status: 404 });
    }

    const worksheetData = worksheet as unknown as WorksheetData;
    const items = worksheetData.worksheet_items.sort((a, b) => a.position - b.position);

    const pdfUrls = items
      .map((item) => {
        if (!item.questions) return null;
        if (type === 'markscheme') {
          return toAbsolutePdfUrl(item.questions.ms_pdf_url);
        }
        return toAbsolutePdfUrl(item.questions.page_pdf_url);
      })
      .filter(Boolean) as string[];

    if (pdfUrls.length === 0) {
      return NextResponse.json({ error: 'No PDFs found' }, { status: 404 });
    }

    const params = worksheetData.params ?? {};
    const coverTitle = worksheetData.title || worksheetData.subjects?.name || 'Worksheet';

    const mergedPdf = await PDFDocument.create();

    await buildCoverPage(mergedPdf, {
      type: type as 'worksheet' | 'markscheme',
      subjectName: coverTitle,
      level: worksheetData.subjects?.level ?? '',
      topics: params.topics ?? [],
      yearStart: params.yearStart ?? null,
      yearEnd: params.yearEnd ?? null,
      difficulty: params.difficulty ?? null,
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