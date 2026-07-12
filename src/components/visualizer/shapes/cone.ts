// Cone template. Special construction: highlights perpendicular height h (axis)
// versus slant height l (apex → rim) — a major student misconception.

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, scale } from "../core/vec"
import { sectorPoly, circlePoly, face, areaLabel } from "../core/net"

export const cone: ShapeTemplate = {
  id: "cone",
  name: "Cone",
  keywords: ["cone", "conical"],
  params: [
    { key: "r", label: "Radius", symbol: "r", unit: "cm", default: 5, min: 0.1, step: 0.5 },
    { key: "h", label: "Height", symbol: "h", unit: "cm", default: 12, min: 0.1, step: 0.5 },
  ],
  compute: ({ r, h }): ShapeModel => {
    const k = scaleFactor(Math.max(2 * r, h))
    const sr = r * k, sh = h * k
    const apex: Vec3 = [0, sh / 2, 0]
    const baseC: Vec3 = [0, -sh / 2, 0]
    const rim: Vec3 = [sr, -sh / 2, 0]

    const slant = Math.sqrt(r * r + h * h)
    const m = Math.min(sr, sh) * 0.28

    return {
      meshes: [{ kind: "cone", args: [sr, sh, 64], color: "#0ea5e9", opacity: 0.22, edges: true }],
      labels: [
        { text: `r = ${r} cm`, position: add(scale(add(baseC, rim), 0.5), [0, -0.5, 0]), kind: "dimension" },
      ],
      constructionLabels: [
        { text: `h = ${h} cm`, position: add(scale(add(apex, baseC), 0.5), [-0.6, 0, 0]), kind: "dimension" },
        { text: `l = ${slant.toFixed(2)} cm`, position: add(scale(add(apex, rim), 0.5), [0.6, 0, 0]), kind: "angle" },
      ],
      constructionLines: [
        { points: [apex, baseC], color: "#a78bfa", width: 4 }, // perpendicular height
        { points: [baseC, rim], color: "#22d3ee", width: 4 }, // radius
        { points: [apex, rim], color: "#f97316", width: 5 }, // slant height
        { points: [add(baseC, [0, m, 0]), add(baseC, [m, m, 0]), add(baseC, [m, 0, 0])], color: "#94a3b8", width: 2 },
      ],
      working: [
        { title: "Slant height l = √(r² + h²)", detail: `= √(${r}² + ${h}²) = ${slant.toFixed(2)} cm`, color: "#f97316" },
        { title: "Volume V = ⅓πr²h", detail: `= ⅓·π·${r}²·${h} = ${((Math.PI * r * r * h) / 3).toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Curved surface = πrl", detail: `= π·${r}·${slant.toFixed(2)} = ${(Math.PI * r * slant).toFixed(2)} cm²`, color: "#22d3ee" },
        { title: "Total surface = πr(r + l)", detail: `= ${(Math.PI * r * (r + slant)).toFixed(2)} cm²` },
      ],
      // Net: a sector (curved surface; arc length = base circumference) + base circle.
      net: (() => {
        const slantScene = Math.sqrt(sr * sr + sh * sh)
        const angle = (2 * Math.PI * sr) / slantScene
        const start = -Math.PI / 2 - angle / 2 // fan opens downward from the apex
        const baseCy = -(slantScene + sr + 0.6)
        return [
          face(sectorPoly(0, 0, slantScene, angle, start), "#0ea5e9", areaLabel(Math.PI * r * slant), [0, -slantScene * 0.5]),
          face(circlePoly(0, baseCy, sr), "#38bdf8", areaLabel(Math.PI * r * r), [0, baseCy]),
        ]
      })(),
      metrics: { volume: (Math.PI * r * r * h) / 3, surfaceArea: Math.PI * r * (r + slant) },
    }
  },
}
