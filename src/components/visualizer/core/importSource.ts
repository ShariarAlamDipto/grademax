// Reads a dropped file (image or PDF) into { previewUrl, text } entirely in the
// browser — $0, no upload, and fully offline. All Tesseract assets (worker, core
// WASM, English language data) are self-hosted under /public/tesseract so OCR
// never depends on a CDN.

import type { Worker } from "tesseract.js"

let pdfjsCache: typeof import("pdfjs-dist") | null = null
async function getPdfjs() {
  if (!pdfjsCache) {
    pdfjsCache = await import("pdfjs-dist")
    pdfjsCache.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs"
  }
  return pdfjsCache
}

export type ImportSource = "pdf-text" | "ocr"

export interface ImportOutput {
  previewUrl: string
  text: string
  source: ImportSource
  /** True when OCR was attempted but failed — the image still shows for manual entry. */
  ocrFailed?: boolean
}

type Progress = (stage: string, pct?: number) => void

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.onerror = reject
    r.readAsDataURL(file)
  })
}

// ── Tesseract worker, created once with local asset paths ───────────────────
let workerPromise: Promise<Worker> | null = null
let progressCb: Progress | undefined

async function getWorker(): Promise<Worker> {
  if (!workerPromise) {
    const { createWorker } = await import("tesseract.js")
    workerPromise = createWorker("eng", 1, {
      workerPath: "/tesseract/worker.min.js",
      corePath: "/tesseract",
      langPath: "/tesseract/lang",
      logger: (m: { status: string; progress: number }) => {
        if (m.status === "recognizing text") progressCb?.("Reading text (OCR)…", m.progress)
        else progressCb?.(`Preparing OCR… (${m.status})`)
      },
    }).catch((e) => {
      workerPromise = null // allow a retry on next import
      throw e
    })
  }
  return workerPromise
}

async function ocr(image: HTMLCanvasElement | File, onProgress?: Progress): Promise<string> {
  progressCb = onProgress
  const worker = await getWorker()
  const { data } = await worker.recognize(image)
  return data.text
}

/** OCR that never throws — returns "" on failure so the diagram still shows. */
async function ocrSafe(image: HTMLCanvasElement | File, onProgress?: Progress): Promise<{ text: string; ok: boolean }> {
  try {
    const text = await ocr(image, onProgress)
    return { text, ok: text.trim().length > 0 }
  } catch {
    return { text: "", ok: false }
  }
}

/** Upscale small images and convert to greyscale — markedly better OCR on screenshots. */
async function preprocess(file: File): Promise<HTMLCanvasElement> {
  const url = URL.createObjectURL(file)
  try {
    const img = await new Promise<HTMLImageElement>((res, rej) => {
      const im = new Image()
      im.onload = () => res(im)
      im.onerror = rej
      im.src = url
    })
    const scale = Math.min(3, Math.max(1, 1600 / Math.max(img.width, img.height, 1)))
    const c = document.createElement("canvas")
    c.width = Math.round(img.width * scale)
    c.height = Math.round(img.height * scale)
    const ctx = c.getContext("2d")!
    ctx.drawImage(img, 0, 0, c.width, c.height)
    const data = ctx.getImageData(0, 0, c.width, c.height)
    const px = data.data
    for (let i = 0; i < px.length; i += 4) {
      const g = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
      px[i] = px[i + 1] = px[i + 2] = g
    }
    ctx.putImageData(data, 0, 0)
    return c
  } finally {
    URL.revokeObjectURL(url)
  }
}

async function renderPdfPage(file: File): Promise<{ canvas: HTMLCanvasElement; text: string }> {
  const pdfjs = await getPdfjs()
  const buf = await file.arrayBuffer()
  const pdf = await pdfjs.getDocument({ data: buf, isEvalSupported: false }).promise
  const page = await pdf.getPage(1)

  const viewport = page.getViewport({ scale: 2 })
  const canvas = document.createElement("canvas")
  canvas.width = Math.ceil(viewport.width)
  canvas.height = Math.ceil(viewport.height)
  const ctx = canvas.getContext("2d")!
  await page.render({ canvas, canvasContext: ctx, viewport }).promise

  const content = await page.getTextContent()
  const text = content.items.map((i) => ("str" in i ? i.str : "")).join(" ")
  return { canvas, text }
}

export async function readImport(file: File, onProgress?: Progress): Promise<ImportOutput> {
  const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name)

  if (isPdf) {
    onProgress?.("Opening PDF…")
    const { canvas, text } = await renderPdfPage(file)
    const previewUrl = canvas.toDataURL("image/png")
    if (text.trim().length >= 15) return { previewUrl, text, source: "pdf-text" }
    const { text: ocrText, ok } = await ocrSafe(canvas, onProgress)
    return { previewUrl, text: ocrText, source: "ocr", ocrFailed: !ok }
  }

  // Image: show the preview FIRST, then OCR a preprocessed copy. OCR failure is
  // non-fatal — the teacher still sees the exact diagram and can type values.
  onProgress?.("Loading image…")
  const previewUrl = await fileToDataUrl(file)
  let ocrImg: HTMLCanvasElement | File = file
  try {
    ocrImg = await preprocess(file)
  } catch {
    /* fall back to the raw file */
  }
  const { text, ok } = await ocrSafe(ocrImg, onProgress)
  return { previewUrl, text, source: "ocr", ocrFailed: !ok }
}
