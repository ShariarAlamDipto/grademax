// Shared 2D-plot helpers used by the function-graph and area-under-curve shapes:
// the function presets, sampling (with asymptote splitting), and the axes/grid.

import type { Vec3, SceneLine, SceneLabel } from "./types"

export const FUNCS: { label: string; f: (x: number) => number; expr: string }[] = [
  { label: "f(x) = x²", f: (x) => x * x, expr: "x²" },
  { label: "f(x) = x³", f: (x) => x ** 3, expr: "x³" },
  { label: "f(x) = 1/x", f: (x) => (x === 0 ? NaN : 1 / x), expr: "1/x" },
  { label: "f(x) = √x", f: (x) => (x < 0 ? NaN : Math.sqrt(x)), expr: "√x" },
  { label: "f(x) = sin x", f: (x) => Math.sin(x), expr: "sin x" },
  { label: "f(x) = cos x", f: (x) => Math.cos(x), expr: "cos x" },
]

export const W = 6 // window: x, y ∈ [−6, 6] (scene units)
export const YMAX = 6.4
const N = 240

/** Sample a function across the window, splitting into segments at gaps/asymptotes. */
export function sample(f: (x: number) => number): Vec3[][] {
  const segs: Vec3[][] = []
  let cur: Vec3[] = []
  for (let i = 0; i <= N; i++) {
    const x = -W + (2 * W * i) / N
    const y = f(x)
    if (Number.isFinite(y) && Math.abs(y) <= YMAX) {
      cur.push([x, y, 0])
    } else if (cur.length > 1) {
      segs.push(cur)
      cur = []
    } else {
      cur = []
    }
  }
  if (cur.length > 1) segs.push(cur)
  return segs
}

/** Integer grid + the two axes, as scene lines. */
export function gridAxisLines(): SceneLine[] {
  const lines: SceneLine[] = []
  for (let i = -W; i <= W; i++) {
    if (i === 0) continue
    lines.push({ points: [[i, -W, 0], [i, W, 0]], color: "#16233b", width: 1 })
    lines.push({ points: [[-W, i, 0], [W, i, 0]], color: "#16233b", width: 1 })
  }
  lines.push({ points: [[-W, 0, 0], [W, 0, 0]], color: "#64748b", width: 2 })
  lines.push({ points: [[0, -W, 0], [0, W, 0]], color: "#64748b", width: 2 })
  return lines
}

/** Sparse numeric tick labels on both axes plus the origin. */
export function axisTicks(): SceneLabel[] {
  const ticks: SceneLabel[] = []
  for (const t of [-4, -2, 2, 4]) {
    ticks.push({ text: `${t}`, position: [t, -0.45, 0], kind: "dimension" })
    ticks.push({ text: `${t}`, position: [-0.4, t, 0], kind: "dimension" })
  }
  ticks.push({ text: "O", position: [-0.4, -0.45, 0], kind: "dimension" })
  return ticks
}
