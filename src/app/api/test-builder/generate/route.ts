import { NextResponse } from 'next/server';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';
import { mergePagePdfs } from '@/lib/pdfUtils';

async function buildCoverPage(
  doc: PDFDocument,
  opts: {
    title: string;
    totalMarks: number;
    subjectName: string;
    level: string;
    type: 'worksheet' | 'markscheme';
  }
) {
  const page = doc.addPage(PageSizes.A4);
  const { width, height } = page.getSize();

  const bold = await doc.embedFont(StandardFonts.TimesRomanBold);
  const regular = await doc.embedFont(StandardFonts.TimesRoman);
  const black = rgb(0, 0, 0);
  const gray = rgb(0.4, 0.4, 0.4);

  const headerText = 'GradeMax Exams';
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

  const typeLabel = opts.type === 'markscheme' ? 'MARK SCHEME' : 'QUESTION PAPER';
  const labelW = bold.widthOfTextAtSize(typeLabel, 11);
  page.drawText(typeLabel, {
    x: (width - labelW) / 2,
    y: height - 210,
    size: 11,
    font: bold,
    color: gray,
  });

  const displayTitle = opts.title || 'Untitled Test';
  const titleSize = displayTitle.length > 30 ? 22 : 28;
  const titleW = bold.widthOfTextAtSize(displayTitle, titleSize);
  page.drawText(displayTitle, {
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
      y: height - 280,
      size: 12,
      font: regular,
      color: gray,
    });
  }

  const ruleW = 260;
  page.drawRectangle({
    x: (width - ruleW) / 2,
    y: height - 310,
    width: ruleW,
    height: 0.5,
    color: rgb(0.7, 0.7, 0.7),
  });

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
      page.drawRectangle({ x: lineStartX, y: y - 2, width: lineEndX - lineStartX, height: 0.5, color: rgb(0.6, 0.6, 0.6) });
    }
  };

  drawField('Name:', null, fieldStartY);
  drawField('Total Marks:', String(opts.totalMarks), fieldStartY - fieldGap);
  drawField('Marks Received:', null, fieldStartY - fieldGap * 2);

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

interface GenerateBody {
  title: string;
  type: 'worksheet' | 'markscheme';
  totalMarks: number;
  subjectName?: string;
  level?: string;
  pages: { qpPageUrl: string; msPageUrl: string | null }[];
}

export async function POST(request: Request) {
  try {
    const body: GenerateBody = await request.json();
    const { title, type = 'worksheet', totalMarks, subjectName, level, pages } = body;

    if (!pages || pages.length === 0) {
      return NextResponse.json(
        { error: 'At least one page is required' },
        { status: 400 }
      );
    }

    const pdfUrls = pages
      .map(p => type === 'markscheme' ? p.msPageUrl : p.qpPageUrl)
      .filter(Boolean) as string[];

    if (pdfUrls.length === 0) {
      return NextResponse.json(
        { error: `No ${type === 'markscheme' ? 'mark scheme' : 'question paper'} PDFs available for these questions` },
        { status: 404 }
      );
    }

    const mergedPdf = await PDFDocument.create();

    await buildCoverPage(mergedPdf, {
      title: title || 'Untitled Test',
      totalMarks: totalMarks || pages.length * 4,
      subjectName: subjectName || '',
      level: level || '',
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
    const filename = `${(title || 'test').replace(/[^a-zA-Z0-9 ]/g, '').replace(/\s+/g, '_')}_${type}.pdf`;

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
