import * as PdfLib from 'pdf-lib';
import type { PDFDocument } from 'pdf-lib';
import {
  assembleQuestionPdfs,
  type AssemblyKind,
  type AssemblyResult,
  type QuestionSource,
} from './questionPdfAssembly';

const SUPABASE_STORAGE_BASE = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/question-pdfs`;

/**
 * Converts a relative storage path (e.g. "subjects/Chemistry/pages/.../q1.pdf")
 * into a full URL. Already-absolute URLs (https://...) are returned unchanged.
 */
export function toAbsolutePdfUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `${SUPABASE_STORAGE_BASE}/${url.replace(/^\/+/, '')}`;
}

export async function downloadPDF(url: string): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
    if (!response.ok) return null;
    return await response.arrayBuffer();
  } catch {
    return null;
  }
}

/**
 * Appends one slot per question to mergedPdf, in order. A question whose PDF
 * is missing or fails to download gets a placeholder page, so the questions
 * after it never shift into its slot. See questionPdfAssembly.ts.
 */
export async function mergeQuestionPdfs(
  mergedPdf: PDFDocument,
  sources: QuestionSource[],
  kind: AssemblyKind,
): Promise<AssemblyResult> {
  return assembleQuestionPdfs(mergedPdf, PdfLib, sources, kind, downloadPDF);
}
