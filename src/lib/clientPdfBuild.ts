/**
 * Browser-side PDF builder.
 *
 * Background:
 *   The server-side merge route needs a single long-lived response — Vercel
 *   merges N source PDFs and streams the result back as one binary blob.
 *   On phones over cellular, that single response routinely exceeded the
 *   serverless timeout (or the carrier dropped the long transfer), which
 *   surfaced as `Failed to fetch` / a Generate button stuck on
 *   "Generating…" forever.
 *
 *   Doing the merge in the browser sidesteps both problems:
 *     - source PDFs are fetched in parallel from Supabase's CDN,
 *     - there is no single big response that the platform can guillotine,
 *     - and we get free, granular progress feedback for the UI.
 *
 *   pdf-lib runs unchanged in the browser. We dynamic-import it so the
 *   library isn't pulled into the initial JS bundle for users who never
 *   click Generate.
 */

import {
  assembleQuestionPdfs,
  planQuestionSources,
  type QuestionSourceMeta,
} from './questionPdfAssembly';

export interface PdfBuildPage extends QuestionSourceMeta {
  qpPageUrl: string;
  msPageUrl: string | null;
}

export type PdfBuildKind = 'worksheet' | 'markscheme';

export interface PdfBuildOptions {
  kind: PdfBuildKind;
  title: string;
  subjectName: string;
  level: string;
  totalMarks: number;
  /** Brand text drawn at the top of the cover page. */
  brand: string;
  /** When provided, the cover page lists the topic codes used. */
  topics?: string[];
  /** When provided, the cover page lists the year range. */
  yearStart?: number | null;
  yearEnd?: number | null;
  /** When provided, the cover page lists the difficulty filter. */
  difficulty?: string | null;
}

export interface PdfBuildProgress {
  step: 'downloading' | 'merging' | 'finalizing' | 'done';
  done: number;
  total: number;
  label: string;
}

export interface PdfBuildResult {
  blob: Blob;
  /** Number of questions whose PDF was merged in successfully. */
  successCount: number;
  /** Questions that exist in the worksheet (each keeps its slot). */
  attemptedCount: number;
  /** Questions that got a "not available" page instead of a PDF. */
  placeholderCount: number;
}

/**
 * Download one PDF from storage and return its bytes, or null on any
 * error (network, non-2xx, abort). Errors are intentionally swallowed —
 * an individual missing PDF should not abort the whole worksheet.
 */
async function fetchPdfBytes(url: string, signal?: AbortSignal): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(url, { signal, cache: 'force-cache' });
    if (!response.ok) return null;
    return await response.arrayBuffer();
  } catch {
    return null;
  }
}

export async function buildPdfInBrowser(
  pages: PdfBuildPage[],
  opts: PdfBuildOptions,
  onProgress?: (p: PdfBuildProgress) => void,
  signal?: AbortSignal,
): Promise<PdfBuildResult> {
  const lib = await import('pdf-lib');
  const { PDFDocument, StandardFonts, rgb, PageSizes } = lib;

  const merged = await PDFDocument.create();
  const bold = await merged.embedFont(StandardFonts.TimesRomanBold);
  const regular = await merged.embedFont(StandardFonts.TimesRoman);

  // ── Cover page ─────────────────────────────────────────────────────────
  {
    const page = merged.addPage(PageSizes.A4);
    const { width, height } = page.getSize();
    const black = rgb(0, 0, 0);
    const gray = rgb(0.4, 0.4, 0.4);

    const headerText = opts.brand;
    const targetW = width * 0.7;
    const headerSize = targetW / bold.widthOfTextAtSize(headerText, 1);
    const headerW = bold.widthOfTextAtSize(headerText, headerSize);
    page.drawText(headerText, {
      x: (width - headerW) / 2,
      y: height - 160,
      size: headerSize,
      font: bold,
      color: black,
    });

    const typeLabel = opts.kind === 'markscheme' ? 'MARK SCHEME' : 'QUESTION PAPER';
    const labelW = bold.widthOfTextAtSize(typeLabel, 11);
    page.drawText(typeLabel, {
      x: (width - labelW) / 2,
      y: height - 210,
      size: 11,
      font: bold,
      color: gray,
    });

    const displayTitle = opts.title || 'Untitled';
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
        page.drawRectangle({
          x: lineStartX,
          y: y - 2,
          width: lineEndX - lineStartX,
          height: 0.5,
          color: rgb(0.6, 0.6, 0.6),
        });
      }
    };

    drawField('Name:', null, fieldStartY);
    drawField('Total Marks:', String(opts.totalMarks), fieldStartY - fieldGap);
    drawField('Marks Received:', null, fieldStartY - fieldGap * 2);

    if (opts.topics && opts.topics.length > 0) {
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

    const brandFooter = 'GradeMax';
    const brandW = regular.widthOfTextAtSize(brandFooter, 9);
    page.drawText(brandFooter, {
      x: (width - brandW) / 2,
      y: 40,
      size: 9,
      font: regular,
      color: rgb(0.7, 0.7, 0.7),
    });
  }

  // ── Source pages ───────────────────────────────────────────────────────
  // Every question keeps its slot: a missing or failed PDF becomes a
  // placeholder page rather than letting the next question's pages move up
  // (see questionPdfAssembly.ts for the bug this prevents).
  const sources = planQuestionSources(pages, opts.kind);
  const total = sources.length;
  const { merged: successCount, placeholders } = await assembleQuestionPdfs(
    merged,
    lib,
    sources,
    opts.kind,
    (url) => fetchPdfBytes(url, signal),
    ({ done }) =>
      onProgress?.({
        step: done < total ? 'downloading' : 'merging',
        done,
        total,
        label: `Added ${done} of ${total}`,
      }),
    signal,
  );

  onProgress?.({
    step: 'finalizing',
    done: total,
    total,
    label: 'Finalizing PDF…',
  });

  const bytes = await merged.save();
  // pdf-lib returns `Uint8Array<ArrayBufferLike>`. The Blob constructor in
  // recent lib.dom expects an ArrayBuffer-backed view, so we copy into a
  // plain ArrayBuffer slice to satisfy the BlobPart type.
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  const blob = new Blob([buffer], { type: 'application/pdf' });

  onProgress?.({ step: 'done', done: total, total, label: 'PDF ready' });

  return { blob, successCount, attemptedCount: total, placeholderCount: placeholders };
}
