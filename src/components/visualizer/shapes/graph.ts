// Function graph with transformations (IGCSE / Further Pure). Plots y = f(x) and
// the transformation y = a·f(bx + c) + d on labelled axes, so students see the
// effect of each parameter. Built entirely from lines — no 3D mesh.

import type { ShapeTemplate, ShapeModel, SceneLine } from "../core/types"
import { FUNCS, gridAxisLines, axisTicks, sample, W } from "../core/curves"

export const graph: ShapeTemplate = {
  id: "graph",
  name: "Function graph",
  keywords: ["graph", "sketch the curve", "sketch the graph", "transformation of"],
  params: [
    { key: "func", label: "Function", symbol: "", unit: "", default: 0, min: 0, step: 1, choices: FUNCS.map((c, i) => ({ label: c.label, value: i })) },
    { key: "a", label: "a — vertical stretch ×a", symbol: "a", unit: "", default: 1, min: -10, step: 0.5 },
    { key: "b", label: "b — horizontal stretch ×1/b", symbol: "b", unit: "", default: 1, min: -10, step: 0.5 },
    { key: "c", label: "c — shift (inside)", symbol: "c", unit: "", default: 0, min: -10, step: 0.5 },
    { key: "d", label: "d — shift up", symbol: "d", unit: "", default: 0, min: -10, step: 0.5 },
  ],
  compute: ({ func, a, b, c, d }): ShapeModel => {
    const fn = FUNCS[Math.max(0, Math.min(FUNCS.length - 1, Math.round(func)))]
    const base = fn.f
    const transformed = (x: number) => a * base(b * x + c) + d

    const lines: SceneLine[] = gridAxisLines()
    sample(base).forEach((seg) => lines.push({ points: seg, color: "#64748b", width: 2.5, dashed: true }))
    sample(transformed).forEach((seg) => lines.push({ points: seg, color: "#f97316", width: 5 }))

    const sign = (n: number) => (n >= 0 ? `+ ${n}` : `− ${Math.abs(n)}`)

    return {
      meshes: [],
      labels: [{ text: fn.label, position: [-W + 1, W - 0.5, 0], kind: "dimension" }, ...axisTicks()],
      constructionLabels: [],
      constructionLines: lines,
      working: [
        { title: "Base curve", detail: `y = ${fn.expr}`, color: "#64748b" },
        { title: "Transformed (orange)", detail: `y = ${a}·f(${b}x ${sign(c)}) ${sign(d)}`, color: "#f97316" },
        { title: "a — vertical stretch", detail: `×${a}${a < 0 ? " (reflect in x-axis)" : ""}`, color: "#a78bfa" },
        { title: "b — horizontal stretch", detail: `×${b === 0 ? "∞" : +(1 / b).toFixed(3)}${b < 0 ? " (reflect in y-axis)" : ""}`, color: "#22d3ee" },
        { title: "c, d — translations", detail: `inside ${c} shifts horizontally; ${d} shifts vertically`, color: "#cbd5e1" },
      ],
    }
  },
}
