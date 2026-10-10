/**
 * Assembles per-question PDFs into one document, keeping every question in
 * its slot.
 *
 * Why this exists
 * ---------------
 * The worksheet and test-builder mark schemes used to be built from a list of
 * URLs with the missing ones filtered out. When question 3 had no mark scheme
 * (or its download failed), question 4's scheme became the third one in the
 * PDF, and every answer after it sat under the wrong question. Nothing on the
 * page said which question an answer belonged to, so a student had no way to
 * notice: they just saw a mark scheme that "does not belong" to the question.
 *
 * Two rules fix that, for the question paper and the mark scheme alike:
 *   1. A question never loses its slot. No PDF -> a placeholder page that says
 *      so, naming the paper and question it would have come from.
 *   2. Every question's first page carries a header saying which worksheet
 *      question it is and where it came from, so the two PDFs can be matched
 *      by eye even if something upstream goes wrong.
 *
 * pdf-lib is passed in rather than imported: the browser loads it with a
 * dynamic import (keeping it out of the initial bundle) and the server imports
 * it statically. Both run this same code.
 */

import type * as PdfLib from 'pdf-lib';

export type AssemblyKind = 'worksheet' | 'markscheme';

export interface QuestionSourceMeta {
  questionNumber?: string | number | null;
  year?: number | string | null;
  season?: string | null;
  paper?: string | null;
}

export interface QuestionSource {
  /** Absolute URL of this question's PDF, or null when none exists. */
  url: string | null;
  /** Header printed on the question's first page, e.g. "Q3 · 2019 May/Jun · Paper 1R · Question 5". */
  label: string;
}

export interface AssemblyProgress {
  done: number;
  total: number;
}

export interface AssemblyResult {
  /** Questions whose PDF was merged in. */
  merged: number;
  /** Questions that got a placeholder page instead. */
  placeholders: number;
}

export type PdfFetcher = (url: string) => Promise<ArrayBuffer | null>;

const A4_W = 595.28;
const A4_H = 841.89;
/** Band kept clear at the top of every page for the question header. */
const HEADER_BAND = 22;
const HEADER_SIZE = 8;
const BATCH_SIZE = 5;

const SEASON_LABELS: Record<string, string> = {
  jan: 'Jan',
  'may-jun': 'May/Jun',
  'oct-nov': 'Oct/Nov',
  'feb-mar': 'Feb/Mar',
  specimen: 'Specimen',
};

export function formatSeason(season: string | null | undefined): string {
  if (!season) return '';
  return SEASON_LABELS[season.toLowerCase()] ?? season;
}

/** "Q3 · 2019 May/Jun · Paper 1R · Question 5" (parts are omitted when unknown). */
export function questionLabel(position: number, meta: QuestionSourceMeta = {}): string {
  const session = [meta.year, formatSeason(meta.season)].filter(Boolean).join(' ');
  const parts = [
    `Q${position}`,
    session,
    meta.paper ? `Paper ${meta.paper}` : '',
    meta.questionNumber !== undefined && meta.questionNumber !== null && meta.questionNumber !== ''
      ? `Question ${meta.questionNumber}`
      : '',
  ];
  return parts.filter(Boolean).join(' · ');
}

/**
 * One source per question, in worksheet order. A question without a PDF of
 * this kind keeps its slot with `url: null` -- never filtered out.
 */
export function planQuestionSources(
  pages: ReadonlyArray<{ qpPageUrl: string | null; msPageUrl: string | null } & QuestionSourceMeta>,
  kind: AssemblyKind,
): QuestionSource[] {
  return pages.map((page, index) => ({
    url: (kind === 'markscheme' ? page.msPageUrl : page.qpPageUrl) || null,
    label: questionLabel(index + 1, page),
  }));
}

function drawHeader(page: PdfLib.PDFPage, font: PdfLib.PDFFont, lib: typeof PdfLib, label: string): void {
  page.drawText(label, {
    x: 36,
    y: A4_H - 15,
    size: HEADER_SIZE,
    font,
    color: lib.rgb(0.35, 0.35, 0.35),
  });
}

function addPlaceholder(
  doc: PdfLib.PDFDocument,
  lib: typeof PdfLib,
  fonts: { bold: PdfLib.PDFFont; regular: PdfLib.PDFFont },
  label: string,
  kind: AssemblyKind,
): void {
  const page = doc.addPage([A4_W, A4_H]);
  drawHeader(page, fonts.regular, lib, label);
  const title = kind === 'markscheme' ? 'Mark scheme not available' : 'Question not available';
  const note =
    kind === 'markscheme'
      ? 'We do not have a verified mark scheme for this question yet. Check the full paper\'s mark scheme.'
      : 'This question could not be downloaded. Please regenerate the worksheet.';
  const titleSize = 16;
  page.drawText(title, {
    x: (A4_W - fonts.bold.widthOfTextAtSize(title, titleSize)) / 2,
    y: A4_H / 2 + 20,
    size: titleSize,
    font: fonts.bold,
    color: lib.rgb(0.2, 0.2, 0.2),
  });
  const noteSize = 10;
  page.drawText(note, {
    x: Math.max(36, (A4_W - fonts.regular.widthOfTextAtSize(note, noteSize)) / 2),
    y: A4_H / 2 - 4,
    size: noteSize,
    font: fonts.regular,
    color: lib.rgb(0.4, 0.4, 0.4),
  });
}

async function appendSource(
  doc: PdfLib.PDFDocument,
  lib: typeof PdfLib,
  font: PdfLib.PDFFont,
  bytes: ArrayBuffer,
  label: string,
): Promise<void> {
  const src = await lib.PDFDocument.load(bytes);
  const indices = src.getPageIndices();
  if (indices.length === 0) throw new Error('source PDF has no pages');
  const embedded = await doc.embedPdf(src, indices);
  embedded.forEach((page, i) => {
    const target = doc.addPage([A4_W, A4_H]);
    const scale = Math.min(A4_W / page.width, (A4_H - HEADER_BAND) / page.height, 1);
    const w = page.width * scale;
    const h = page.height * scale;
    target.drawPage(page, { x: (A4_W - w) / 2, y: A4_H - HEADER_BAND - h, width: w, height: h });
    if (i === 0) drawHeader(target, font, lib, label);
  });
}

/**
 * Appends every source to `doc` in order. Fetches run in parallel batches;
 * pages are appended strictly in source order, so a slow or failed download
 * can never move another question's pages.
 */
export async function assembleQuestionPdfs(
  doc: PdfLib.PDFDocument,
  lib: typeof PdfLib,
  sources: ReadonlyArray<QuestionSource>,
  kind: AssemblyKind,
  fetchPdf: PdfFetcher,
  onProgress?: (p: AssemblyProgress) => void,
  signal?: AbortSignal,
): Promise<AssemblyResult> {
  const fonts = {
    bold: await doc.embedFont(lib.StandardFonts.HelveticaBold),
    regular: await doc.embedFont(lib.StandardFonts.Helvetica),
  };
  let merged = 0;
  let placeholders = 0;

  for (let start = 0; start < sources.length; start += BATCH_SIZE) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    const batch = sources.slice(start, start + BATCH_SIZE);
    const bodies = await Promise.all(
      batch.map((source) => (source.url ? fetchPdf(source.url).catch(() => null) : Promise.resolve(null))),
    );

    for (let i = 0; i < batch.length; i++) {
      const { label } = batch[i];
      const body = bodies[i];
      let ok = false;
      if (body) {
        try {
          await appendSource(doc, lib, fonts.regular, body, label);
          ok = true;
        } catch (err) {
          console.warn('[questionPdfAssembly] could not merge a source PDF', label, err);
        }
      }
      if (ok) {
        merged += 1;
      } else {
        addPlaceholder(doc, lib, fonts, label, kind);
        placeholders += 1;
      }
      onProgress?.({ done: start + i + 1, total: sources.length });
    }
  }

  return { merged, placeholders };
}
