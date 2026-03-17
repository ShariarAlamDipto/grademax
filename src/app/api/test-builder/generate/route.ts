import { NextResponse } from 'next/server';
import { PDFDocument, StandardFonts, rgb, PageSizes } from 'pdf-lib';

/**
 * POST /api/test-builder/generate
 *
 * Generate a merged PDF directly from page URLs — no database tables needed.
 * This bypasses the tests/test_items tables entirely.
 *
 * Body: {
 *   title: string,
 *   type: 'worksheet' | 'markscheme',
 *   totalMarks: number,
 *   subjectName?: string,
 *   level?: string,
 *   pages: { qpPageUrl: string, msPageUrl: string | null }[]
 * }
 *
 * Returns: PDF binary with Content-Disposition attachment header.
 */

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

  // ── Centered label ──
  const typeLabel = opts.type === 'markscheme' ? 'MARK SCHEME' : 'QUESTION PAPER';
  const labelW = bold.widthOfTextAtSize(typeLabel, 11);
  page.drawText(typeLabel, {
    x: (width - labelW) / 2,
    y: height - 200,
    size: 11,
    font: bold,
    color: gray,
  });

  // ── Brand title (70% width) ──
  const brandTitle = 'GradeMax Exams';
  const targetWidth = width * 0.7;
  const baseWidth = bold.widthOfTextAtSize(brandTitle, 1);
  const computedBrandSize = targetWidth / baseWidth;
  const brandSize = Math.max(28, Math.min(56, computedBrandSize));
  const brandW = bold.widthOfTextAtSize(brandTitle, brandSize);
  page.drawText(brandTitle, {
    x: (width - brandW) / 2,
    y: height - 250,
    size: brandSize,
    font: bold,
    color: black,
  });

  // ── Title ──
  const displayTitle = opts.title || 'Untitled Test';
  const titleSize = displayTitle.length > 30 ? 16 : 20;
  const titleW = bold.widthOfTextAtSize(displayTitle, titleSize);
  page.drawText(displayTitle, {
    x: (width - titleW) / 2,
    y: height - 305,
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
      y: height - 330,
      size: 12,
      font: regular,
      color: gray,
    });
  }

  // ── Thin rule ──
  const ruleW = 260;
  page.drawRectangle({
    x: (width - ruleW) / 2,
    y: height - 350,
    width: ruleW,
    height: 0.5,
    color: rgb(0.7, 0.7, 0.7),
  });

  // ── Fields: Name, Total Marks, Marks Received ──
  const fieldStartY = height - 410;
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
  // Keep mark fields intentionally blank: current mark calculation is not reliable.
  drawField('Total Marks:', null, fieldStartY - fieldGap);
  drawField('Marks Received:', null, fieldStartY - fieldGap * 2);

  // ── Bottom branding ──
  const brand = 'GradeMax';
  const footerBrandW = regular.widthOfTextAtSize(brand, 9);
  page.drawText(brand, {
    x: (width - footerBrandW) / 2,
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

    // Determine which URLs to use based on type
    const pdfUrls = pages
      .map(p => type === 'markscheme' ? p.msPageUrl : p.qpPageUrl)
      .filter(Boolean) as string[];

    if (pdfUrls.length === 0) {
      return NextResponse.json(
        { error: `No ${type === 'markscheme' ? 'mark scheme' : 'question paper'} PDFs available for these questions` },
        { status: 404 }
      );
    }

    console.log(`[generate] Building ${type} PDF: "${title}", ${pdfUrls.length} pages`);

    // Create merged PDF
    const mergedPdf = await PDFDocument.create();

    await buildCoverPage(mergedPdf, {
      title: title || 'Untitled Test',
      totalMarks: totalMarks || pages.length * 4,
      subjectName: subjectName || '',
      level: level || '',
      type,
    });

    // Download and merge PDFs in batches — embed into A4
    const [a4W, a4H] = PageSizes.A4;
    let successCount = 0;
    const batchSize = 10;

    for (let i = 0; i < pdfUrls.length; i += batchSize) {
      const batch = pdfUrls.slice(i, i + batchSize);
      const results = await Promise.allSettled(batch.map(u => downloadPDF(u)));

      for (let j = 0; j < results.length; j++) {
        const result = results[j];
        if (result.status !== 'fulfilled' || !result.value) {
          console.warn(`[generate] Failed to download PDF ${i + j + 1}:`, batch[j]?.slice(0, 80));
          continue;
        }
        try {
          const srcPdf = await PDFDocument.load(result.value);
          const pageIndices = srcPdf.getPageIndices();
          for (const pi of pageIndices) {
            const srcPage = srcPdf.getPage(pi);
            const { width: srcW, height: srcH } = srcPage.getSize();
            if (Math.abs(srcW - a4W) < 2 && Math.abs(srcH - a4H) < 2) {
              const [copied] = await mergedPdf.copyPages(srcPdf, [pi]);
              mergedPdf.addPage(copied);
            } else {
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
          console.error(`[generate] Error merging PDF ${i + j + 1}:`, err);
        }
      }
    }

    console.log(`[generate] Merged ${successCount}/${pdfUrls.length} PDFs successfully`);

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
    console.error('[generate] Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate PDF' },
      { status: 500 }
    );
  }
}
