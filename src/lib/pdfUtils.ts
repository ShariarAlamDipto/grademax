import { PDFDocument, PageSizes } from 'pdf-lib';

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
 * Appends all pages from the given URLs into mergedPdf.
 * Each source PDF is embedded into A4, scaled to fit if needed.
 * Returns the number of source PDFs successfully merged.
 */
export async function mergePagePdfs(
  mergedPdf: PDFDocument,
  pdfUrls: string[]
): Promise<number> {
  const [a4W, a4H] = PageSizes.A4;
  const batchSize = 10;
  let successCount = 0;

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
        successCount++;
      } catch {
        // Individual PDF errors are non-fatal; continue with remaining pages
      }
    }
  }

  return successCount;
}
