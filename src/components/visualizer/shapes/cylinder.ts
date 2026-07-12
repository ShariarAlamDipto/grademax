// Cylinder template.

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, scale } from "../core/vec"
import { rect, circlePoly, face, areaLabel } from "../core/net"

export const cylinder: ShapeTemplate = {
  id: "cylinder",
  name: "Cylinder",
  keywords: ["cylinder", "cylindrical", "tube", "pipe"],
  params: [
    { key: "r", label: "Radius", symbol: "r", unit: "cm", default: 4, min: 0.1, step: 0.5 },
    { key: "h", label: "Height", symbol: "h", unit: "cm", default: 10, min: 0.1, step: 0.5 },
  ],
  compute: ({ r, h }): ShapeModel => {
    const k = scaleFactor(Math.max(2 * r, h))
    const sr = r * k, sh = h * k
    const topC: Vec3 = [0, sh / 2, 0]
    const botC: Vec3 = [0, -sh / 2, 0]
    const topRim: Vec3 = [sr, sh / 2, 0]

    return {
      meshes: [{ kind: "cylinder", args: [sr, sr, sh, 64], color: "#10b981", opacity: 0.22, edges: true }],
      labels: [
        { text: `r = ${r} cm`, position: add(scale(add(topC, topRim), 0.5), [0, 0.5, 0]), kind: "dimension" },
        { text: `h = ${h} cm`, position: add(scale(add(topC, botC), 0.5), [sr + 0.6, 0, 0]), kind: "dimension" },
      ],
      constructionLabels: [],
      constructionLines: [
        { points: [topC, topRim], color: "#22d3ee", width: 4 },
        { points: [[sr, sh / 2, 0], [sr, -sh / 2, 0]], color: "#a78bfa", width: 3 },
      ],
      working: [
        { title: "Volume V = πr²h", detail: `= π·${r}²·${h} = ${(Math.PI * r * r * h).toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Curved surface = 2πrh", detail: `= ${(2 * Math.PI * r * h).toFixed(2)} cm²`, color: "#22d3ee" },
        { title: "Total surface = 2πr(r + h)", detail: `= ${(2 * Math.PI * r * (r + h)).toFixed(2)} cm²` },
      ],
      // Net: a rectangle (the curved surface, width = circumference) + 2 circles.
      net: (() => {
        const circ = 2 * Math.PI * sr
        const gap = sr + 0.6
        return [
          face(rect(0, 0, circ, sh), "#10b981", areaLabel(2 * Math.PI * r * h), [0, 0]),
          face(circlePoly(0, sh / 2 + gap, sr), "#34d399", areaLabel(Math.PI * r * r), [0, sh / 2 + gap]),
          face(circlePoly(0, -(sh / 2 + gap), sr), "#34d399", areaLabel(Math.PI * r * r), [0, -(sh / 2 + gap)]),
        ]
      })(),
      metrics: { volume: Math.PI * r * r * h, surfaceArea: 2 * Math.PI * r * (r + h) },
    }
  },
}
