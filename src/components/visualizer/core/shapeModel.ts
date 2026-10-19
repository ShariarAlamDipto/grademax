// In-browser shape recognition. Runs the GPU-trained (PyTorch → ONNX) classifier
// via onnxruntime-web. Fully offline & $0: the model and the ORT wasm are
// self-hosted under /public. Best-effort — any failure returns null and the
// text-based guess stands.
//
// Model: MobileNetV3-Small, 96×96, grayscale-as-RGB, input 0–1 NCHW [1,3,96,96];
// ImageNet normalisation is BAKED INTO the model. Output = 8 logits.
// Trained by scripts/train_torch.py on the local NVIDIA GPU.

import type { ShapeId } from "./types"

const IMG = 96

// Classifier class label → visualizer shape id (pyramid → rectangular pyramid).
const MAP: Record<string, ShapeId> = {
  cuboid: "cuboid",
  cone: "cone",
  cylinder: "cylinder",
  sphere: "sphere",
  hemisphere: "hemisphere",
  pyramid: "rectpyramid",
  prism: "prism",
  frustum: "frustum",
}

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ort?: any
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let session: any = null
let labels: string[] = []

/**
 * Load onnxruntime-web from its self-hosted UMD bundle via a <script> tag.
 * This deliberately bypasses the module bundler (Turbopack mishandles ORT's
 * internal dynamic wasm import), so inference works reliably in the browser.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function loadOrt(): Promise<any> {
  if (window.ort) return Promise.resolve(window.ort)
  return new Promise((resolve, reject) => {
    const done = () => (window.ort ? resolve(window.ort) : reject(new Error("ort global missing after load")))
    const existing = document.querySelector<HTMLScriptElement>("script[data-ort]")
    if (existing) {
      existing.addEventListener("load", done)
      existing.addEventListener("error", () => reject(new Error("ort script failed")))
      if (window.ort) resolve(window.ort)
      return
    }
    const s = document.createElement("script")
    s.src = "/ort/ort.wasm.min.js"
    s.dataset.ort = "1"
    s.onload = done
    s.onerror = () => reject(new Error("failed to load /ort/ort.wasm.min.js"))
    document.head.appendChild(s)
  })
}

export interface VisionResult {
  shape: ShapeId
  score: number
  label: string
}

/** Load image → 96×96 greyscale → 0–1 CHW Float32Array (matches training). */
async function preprocess(url: string): Promise<Float32Array> {
  const img = await new Promise<HTMLImageElement>((res, rej) => {
    const im = new Image()
    im.onload = () => res(im)
    im.onerror = rej
    im.src = url
  })
  const c = document.createElement("canvas")
  c.width = IMG
  c.height = IMG
  const ctx = c.getContext("2d")!
  ctx.fillStyle = "#fff"
  ctx.fillRect(0, 0, IMG, IMG)
  ctx.drawImage(img, 0, 0, IMG, IMG)
  const { data } = ctx.getImageData(0, 0, IMG, IMG)

  const hw = IMG * IMG
  const arr = new Float32Array(3 * hw)
  for (let i = 0; i < hw; i++) {
    const g = (0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2]) / 255
    arr[i] = g // R plane
    arr[hw + i] = g // G plane
    arr[2 * hw + i] = g // B plane
  }
  return arr
}

function softmaxArgmax(logits: Float32Array): { idx: number; score: number } {
  let max = -Infinity
  for (const v of logits) if (v > max) max = v
  let sum = 0
  const exps = Array.from(logits, (v) => { const e = Math.exp(v - max); sum += e; return e })
  let best = 0
  for (let i = 1; i < exps.length; i++) if (exps[i] > exps[best]) best = i
  return { idx: best, score: exps[best] / sum }
}

export async function classifyShapeLocal(imageUrl: string): Promise<VisionResult | null> {
  try {
    const ort = await loadOrt()
    if (!session) {
      ort.env.wasm.wasmPaths = "/ort/"
      ort.env.wasm.numThreads = 1 // single-threaded → no cross-origin-isolation needed
      session = await ort.InferenceSession.create("/models/shape-classifier/shape.onnx")
      labels = await fetch("/models/shape-classifier/labels.json").then((r) => r.json())
    }
    const arr = await preprocess(imageUrl)
    const input = new ort.Tensor("float32", arr, [1, 3, IMG, IMG])
    const out = await session.run({ [session.inputNames[0]]: input })
    const logits = out[session.outputNames[0]].data as Float32Array
    const { idx, score } = softmaxArgmax(logits)
    const label = labels[idx]
    const shape = MAP[label]
    return shape ? { shape, score, label } : null
  } catch (e) {
    // Surface the real reason in the console so failures are diagnosable.
    console.error("[shapeModel] recognition failed:", e)
    return null
  }
}
