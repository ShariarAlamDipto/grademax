// Text → shape + dimensions extractor. Deliberately conservative: it produces a
// best-guess that PRE-FILLS the editable form. It never renders on its own, so a
// wrong guess costs the teacher one correction, never a wrong diagram in class.

import type { ShapeId } from "./types"
import { shapeList, defaultsFor, shapes } from "./registry"

export interface ExtractResult {
  shapeId: ShapeId
  values: Record<string, number>
  confidence: "high" | "medium" | "low"
  note: string
  rawText: string
}

/** First number following any of the given concept words (e.g. "radius = 5"). */
function labelled(text: string, words: string[]): number | null {
  for (const w of words) {
    const re = new RegExp(`\\b${w}\\b\\s*(?:=|is|of|:|length|measures)?\\s*([0-9]+(?:\\.[0-9]+)?)`, "i")
    const m = text.match(re)
    if (m) return parseFloat(m[1])
  }
  return null
}

/** All numbers that carry a length unit, in order of appearance. */
function unitedNumbers(text: string): number[] {
  const out: number[] = []
  const re = /([0-9]+(?:\.[0-9]+)?)\s*(?:cm|mm|metres?|meters?|m)\b/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) out.push(parseFloat(m[1]))
  return out
}

/** Levenshtein distance — used for OCR-tolerant keyword matching. */
function lev(a: string, b: string): number {
  const m = a.length, n = b.length
  const d = Array.from({ length: m + 1 }, (_, i) => [i, ...Array(n).fill(0)])
  for (let j = 0; j <= n; j++) d[0][j] = j
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
  return d[m][n]
}

/** Keyword present, tolerating 1 OCR error on longer single words (e.g. "prismn"). */
function fuzzyHas(text: string, kw: string): boolean {
  if (new RegExp(`\\b${kw}`, "i").test(text)) return true
  if (kw.includes(" ") || kw.length < 5) return false
  const k = kw.toLowerCase()
  const tokens = text.toLowerCase().match(/[a-z]+/g) ?? []
  return tokens.some((t) => Math.abs(t.length - k.length) <= 1 && lev(t, k) <= 1)
}

/** Score by number of distinct keyword hits; earliest shape wins ties. */
function detectShape(text: string): ShapeId | null {
  let best: ShapeId | null = null
  let bestScore = 0
  for (const s of shapeList) {
    const score = s.keywords.reduce((n, kw) => n + (fuzzyHas(text, kw) ? 1 : 0), 0)
    if (score > bestScore) {
      bestScore = score
      best = s.id
    }
  }
  return best
}

/** When no shape keyword is found, guess from which dimensions are mentioned. */
function inferShape(text: string): ShapeId | null {
  const has = (re: RegExp) => re.test(text)
  if (has(/\bslant\b/) && has(/\bradius\b|diameter/)) return "cone"
  if (has(/\bradius\b|diameter/) && has(/\bheight\b|\btall\b/)) return "cylinder"
  if (has(/\bradius\b|diameter/)) return "sphere"
  if (has(/\bslant\b/)) return "rectpyramid"
  return null
}

const CONCEPTS: Record<string, string[]> = {
  r: ["radius", "r"],
  R: ["base radius", "bottom radius", "radius", "r"],
  h: ["height", "high", "tall", "h"],
  // "ab"/"bc" let us read AB = 8, BC = 10 directly off the diagram.
  l: ["ab", "length", "long", "l"],
  w: ["bc", "width", "breadth", "depth", "wide", "w"],
  a: ["side", "base", "edge", "a"],
  // Slant edge EA: "ed = 12" matches the tail of "EA=EB=EC=ED=12".
  e: ["slant edge", "lateral edge", "ea", "eb", "ec", "ed", "slant", "lateral"],
}

export function extractFromText(rawText: string): ExtractResult {
  const text = rawText.replace(/\s+/g, " ").trim()
  const detected = detectShape(text) ?? inferShape(text)
  const shapeId: ShapeId = detected ?? "cuboid"
  const template = shapes[shapeId]
  const values = defaultsFor(shapeId)

  // 1) diameter → radius (takes priority over a bare radius match if present).
  const dia = labelled(text, ["diameter", "across"])

  // 2) Fill each param from a labelled value where possible, tracking which
  //    numbers got consumed so step 3 doesn't reuse them.
  let labelledHits = 0
  const labelledKeys = new Set<string>()
  const used: number[] = []
  for (const p of template.params) {
    if (p.key === "r" && dia != null) {
      values.r = dia / 2
      labelledHits++
      labelledKeys.add("r")
      used.push(dia)
      continue
    }
    const v = labelled(text, CONCEPTS[p.key] ?? [p.key])
    if (v != null && v > 0) {
      values[p.key] = v
      labelledHits++
      labelledKeys.add(p.key)
      used.push(v)
    }
  }

  // 3) Fill un-labelled params from the REMAINING numbers (excluding the ones
  //    already used above), in order of appearance.
  const remaining = unitedNumbers(text)
  for (const u of used) {
    const i = remaining.indexOf(u)
    if (i >= 0) remaining.splice(i, 1)
  }
  let pi = 0
  const filledKeys = new Set<string>()
  for (const p of template.params) {
    if (!labelledKeys.has(p.key) && pi < remaining.length) {
      values[p.key] = remaining[pi++]
      filledKeys.add(p.key)
    }
  }
  const pool = remaining

  const allFilled = labelledHits + filledKeys.size >= template.params.length
  let confidence: ExtractResult["confidence"] = "low"
  if (detected && labelledHits >= template.params.length) confidence = "high"
  else if (detected && allFilled) confidence = "medium"
  else if (detected || pool.length) confidence = "low"

  const note = detected
    ? labelledHits >= template.params.length
      ? "Shape and all dimensions read with labels — please confirm."
      : "Shape recognised; some values guessed from the numbers found — check them."
    : "No shape keyword found — defaulted to cuboid. Pick the right shape and check values."

  return { shapeId, values, confidence, note, rawText }
}
