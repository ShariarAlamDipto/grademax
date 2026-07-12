// Area under a curve (definite integral). Shades the region between y = f(x) and
// the x-axis from x = a to x = b, and reports the numerically integrated value.

import type { ShapeTemplate, ShapeModel, SceneLine, Vec3 } from "../core/types"
import { FUNCS, gridAxisLines, axisTicks, sample, W, YMAX } from "../core/curves"

const STRIPS = 100

export const area: ShapeTemplate = {
  id: "areaundercurve",
  name: "Area under curve",
  keywords: ["area under", "definite integral", "integrate", "area enclosed"],
  params: [
    { key: "func", label: "Function", symbol: "", unit: "", default: 0, min: 0, step: 1, choices: FUNCS.map((c, i) => ({ label: c.label, value: i })) },
    { key: "a", label: "Lower limit a", symbol: "a", unit: "", default: 0, min: -W, step: 0.5 },
    { key: "b", label: "Upper limit b", symbol: "b", unit: "", default: 3, min: -W, step: 0.5 },
  ],
  compute: ({ func, a, b }): ShapeModel => {
    const fn = FUNCS[Math.max(0, Math.min(FUNCS.length - 1, Math.round(func)))]
    const lo = Math.max(-W, Math.min(a, b))
    const hi = Math.min(W, Math.max(a, b, lo + 0.1))

    // Definite integral by the trapezium rule (true signed value).
    let integral = 0
    for (let i = 0; i < STRIPS; i++) {
      const x0 = lo + ((hi - lo) * i) / STRIPS
      const x1 = lo + ((hi - lo) * (i + 1)) / STRIPS
      const y0 = fn.f(x0), y1 = fn.f(x1)
      if (Number.isFinite(y0) && Number.isFinite(y1)) integral += ((y0 + y1) / 2) * (x1 - x0)
    }

    // Shaded region polygon: baseline a→b, then the curve back b→a (clamped to view).
    const clamp = (y: number) => Math.max(-YMAX, Math.min(YMAX, Number.isFinite(y) ? y : 0))
    const ring: Vec3[] = [[lo, 0, 0]]
    for (let i = 0; i <= STRIPS; i++) {
      const x = lo + ((hi - lo) * i) / STRIPS
      ring.push([x, clamp(fn.f(x)), 0])
    }
    ring.push([hi, 0, 0])

    const lines: SceneLine[] = gridAxisLines()
    sample(fn.f).forEach((seg) => lines.push({ points: seg, color: "#f97316", width: 5 }))
    lines.push({ points: [[lo, 0, 0], [lo, clamp(fn.f(lo)), 0]], color: "#22d3ee", width: 2 })
    lines.push({ points: [[hi, 0, 0], [hi, clamp(fn.f(hi)), 0]], color: "#22d3ee", width: 2 })

    return {
      meshes: [{ kind: "polygon2d", args: ring.flatMap((p) => [p[0], p[1]]), color: "#22d3ee", opacity: 0.4 }],
      labels: [
        { text: fn.label, position: [-W + 1, W - 0.5, 0], kind: "dimension" },
        { text: `a = ${lo}`, position: [lo, -0.5, 0], kind: "dimension" },
        { text: `b = ${hi}`, position: [hi, -0.5, 0], kind: "dimension" },
        ...axisTicks(),
      ],
      constructionLabels: [],
      constructionLines: lines,
      working: [
        { title: `Region under y = ${fn.expr}`, detail: `between x = ${lo} and x = ${hi}`, color: "#f97316" },
        { title: "Definite integral ∫ₐᵇ f(x) dx", detail: `≈ ${integral.toFixed(3)} (signed area)`, color: "#22d3ee" },
        { title: "Note", detail: "Area below the x-axis counts as negative in the integral.", color: "#94a3b8" },
      ],
    }
  },
}
