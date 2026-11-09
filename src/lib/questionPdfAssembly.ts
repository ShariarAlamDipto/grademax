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
 * Space-aware layout
 * ------------------
 * Question PDFs are cut to their content, so a 1-mark MCQ is a strip about a
 * fifth of a page tall. Giving every strip its own A4 sheet wasted most of each
 * page (Accounting worksheets were mostly white). Pages are now packed: each
 * source page is drawn whole, below the previous one, while it fits on the
 * current sheet; otherwise it starts a new sheet. A source page is never split,
 * scaled to fit beside another, or reordered, so slot order and the label rule
 * above still hold. Full-height pages behave exactly as before.
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
  /** Questions that got a placeholder block instead. */
  placeholders: number;
}

/** Where one block (a source page or a placeholder) was drawn. */
export interface PlacedBlock {
  /** 0-based index of the question in the worksheet. */
  question: number;
  /** 0-based index of the A4 sheet it landed on. */
  sheet: number;
  /** Top and bottom of the block in PDF points (origin bottom-left). */
  top: number;
  bottom: number;
}

export type PdfFetcher = (url: string) => Promise<ArrayBuffer | null>;

const A4_W = 595.28;
const A4_H = 841.89;
/** Band kept clear above a question's first block for its header label. */
const HEADER_BAND = 22;
const HEADER_SIZE = 8;
/** Label baseline, measured down from the top of its band. */
const HEADER_BASELINE = 15;
/** Space between two blocks stacked on one sheet. */
const BLOCK_GAP = 12;
/** A stacked block must end at least this far above the sheet's bottom edge. */
const BOTTOM_MARGIN = 24;
/** Height of the block that stands in for a missing question or mark scheme. */
const PLACEHOLDER_H = 96;
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

interface Fonts {
  bold: PdfLib.PDFFont;
  regular: PdfLib.PDFFont;
}

/**
 * Packs blocks top to bottom onto A4 sheets. `reserve` returns where the next
 * block goes, opening a new sheet when it does not fit on the current one.
 */
class SheetPacker {
  private page: PdfLib.PDFPage | null = null;
  private sheet = -1;
  /** Top of the free space on the current sheet. */
  private cursor = 0;
  readonly placed: PlacedBlock[] = [];

  constructor(
    private readonly doc: PdfLib.PDFDocument,
    private readonly lib: typeof PdfLib,
    private readonly font: PdfLib.PDFFont,
  ) {}

  /**
   * Reserves `height` points for a block of question `question`. A labelled
   * block (a question's first) gets the header band above it; a stacked block
   * gets a gap and a thin rule separating it from the one above.
   */
  reserve(question: number, height: number, label: string | null): { page: PdfLib.PDFPage; top: number } {
    const band = label ? HEADER_BAND : 0;
    const stackedTop = this.cursor - BLOCK_GAP - band;
    const fits = this.page !== null && stackedTop - height >= BOTTOM_MARGIN;
    let blockTop: number;
    if (fits) {
      const rule = this.cursor - BLOCK_GAP / 2;
      if (label) {
        this.page!.drawLine({
          start: { x: 36, y: rule },
          end: { x: A4_W - 36, y: rule },
          thickness: 0.5,
          color: this.lib.rgb(0.8, 0.8, 0.8),
        });
      }
      blockTop = stackedTop;
    } else {
      this.page = this.doc.addPage([A4_W, A4_H]);
      this.sheet += 1;
      // A fresh sheet keeps the header band clear even for a continuation page,
      // exactly as before packing existed.
      blockTop = A4_H - HEADER_BAND;
    }
    if (label) this.drawLabel(label, blockTop + HEADER_BAND - HEADER_BASELINE);
    this.cursor = blockTop - height;
    this.placed.push({ question, sheet: this.sheet, top: blockTop, bottom: this.cursor });
    return { page: this.page!, top: blockTop };
  }

  private drawLabel(label: string, y: number): void {
    this.page!.drawText(label, {
      x: 36,
      y,
      size: HEADER_SIZE,
      font: this.font,
      color: this.lib.rgb(0.35, 0.35, 0.35),
    });
  }
}

/** Fits a source page to the sheet width and height, never enlarging it. */
function scaledSize(width: number, height: number): { w: number; h: number } {
  const scale = Math.min(A4_W / width, (A4_H - HEADER_BAND) / height, 1);
  return { w: width * scale, h: height * scale };
}

function addPlaceholder(
  packer: SheetPacker,
  lib: typeof PdfLib,
  fonts: Fonts,
  question: number,
  label: string,
  kind: AssemblyKind,
): void {
  const { page, top } = packer.reserve(question, PLACEHOLDER_H, label);
  const title = kind === 'markscheme' ? 'Mark scheme not available' : 'Question not available';
  const note =
    kind === 'markscheme'
      ? 'We do not have a verified mark scheme for this question yet. Check the full paper\'s mark scheme.'
      : 'This question could not be downloaded. Please regenerate the worksheet.';
  const titleSize = 16;
  page.drawText(title, {
    x: (A4_W - fonts.bold.widthOfTextAtSize(title, titleSize)) / 2,
    y: top - PLACEHOLDER_H / 2 + 8,
    size: titleSize,
    font: fonts.bold,
    color: lib.rgb(0.2, 0.2, 0.2),
  });
  const noteSize = 10;
  page.drawText(note, {
    x: Math.max(36, (A4_W - fonts.regular.widthOfTextAtSize(note, noteSize)) / 2),
    y: top - PLACEHOLDER_H / 2 - 16,
    size: noteSize,
    font: fonts.regular,
    color: lib.rgb(0.4, 0.4, 0.4),
  });
}

/**
 * Embeds every page of one source PDF. Embedding happens before anything is
 * drawn, so a source that fails to load leaves no partial pages behind and the
 * caller can put a placeholder in its slot.
 */
async function embedSource(
  doc: PdfLib.PDFDocument,
  lib: typeof PdfLib,
  bytes: ArrayBuffer,
): Promise<PdfLib.PDFEmbeddedPage[]> {
  const src = await lib.PDFDocument.load(bytes);
  const indices = src.getPageIndices();
  if (indices.length === 0) throw new Error('source PDF has no pages');
  return doc.embedPdf(src, indices);
}

function drawSource(
  packer: SheetPacker,
  question: number,
  embedded: PdfLib.PDFEmbeddedPage[],
  label: string,
): void {
  embedded.forEach((page, i) => {
    const { w, h } = scaledSize(page.width, page.height);
    const { page: sheet, top } = packer.reserve(question, h, i === 0 ? label : null);
    sheet.drawPage(page, { x: (A4_W - w) / 2, y: top - h, width: w, height: h });
  });
}

/**
 * Appends every source to `doc` in order, packed onto as few A4 sheets as
 * possible. Fetches run in parallel batches; blocks are placed strictly in
 * source order, so a slow or failed download can never move another
 * question's pages. `onLayout`, when given, receives where every block landed.
 */
export async function assembleQuestionPdfs(
  doc: PdfLib.PDFDocument,
  lib: typeof PdfLib,
  sources: ReadonlyArray<QuestionSource>,
  kind: AssemblyKind,
  fetchPdf: PdfFetcher,
  onProgress?: (p: AssemblyProgress) => void,
  signal?: AbortSignal,
  onLayout?: (blocks: ReadonlyArray<PlacedBlock>) => void,
): Promise<AssemblyResult> {
  const fonts: Fonts = {
    bold: await doc.embedFont(lib.StandardFonts.HelveticaBold),
    regular: await doc.embedFont(lib.StandardFonts.Helvetica),
  };
  const packer = new SheetPacker(doc, lib, fonts.regular);
  let merged = 0;
  let placeholders = 0;

  for (let start = 0; start < sources.length; start += BATCH_SIZE) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    const batch = sources.slice(start, start + BATCH_SIZE);
    const bodies = await Promise.all(
      batch.map((source) => (source.url ? fetchPdf(source.url).catch(() => null) : Promise.resolve(null))),
    );

    for (let i = 0; i < batch.length; i++) {
      const question = start + i;
      const { label } = batch[i];
      const body = bodies[i];
      let embedded: PdfLib.PDFEmbeddedPage[] | null = null;
      if (body) {
        try {
          embedded = await embedSource(doc, lib, body);
        } catch (err) {
          console.warn('[questionPdfAssembly] could not merge a source PDF', label, err);
        }
      }
      if (embedded) {
        drawSource(packer, question, embedded, label);
        merged += 1;
      } else {
        addPlaceholder(packer, lib, fonts, question, label, kind);
        placeholders += 1;
      }
      onProgress?.({ done: question + 1, total: sources.length });
    }
  }

  onLayout?.(packer.placed);
  return { merged, placeholders };
}
