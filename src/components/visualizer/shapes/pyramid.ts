// Square-based pyramid. Built from a 4-sided cone rotated 45° so the base is an
// axis-aligned square of side a. Construction: perpendicular height vs slant.

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, scale } from "../core/vec"
import { rect, tri, face, areaLabel } from "../core/net"

export const pyramid: ShapeTemplate = {
  id: "pyramid",
  name: "Square pyramid",
  keywords: ["square pyramid", "square-based", "square based"],
  params: [
    { key: "a", label: "Base side", symbol: "a", unit: "cm", default: 6, min: 0.1, step: 0.5 },
    { key: "h", label: "Height", symbol: "h", unit: "cm", default: 8, min: 0.1, step: 0.5 },
  ],
  compute: ({ a, h }): ShapeModel => {
    const k = scaleFactor(Math.max(a, h))
    const sa = a * k, sh = h * k
    const apex: Vec3 = [0, sh / 2, 0]
    const baseC: Vec3 = [0, -sh / 2, 0]
    const edgeMid: Vec3 = [sa / 2, -sh / 2, 0] // midpoint of a base edge
    const frontMid: Vec3 = [0, -sh / 2, sa / 2]

    const slant = Math.sqrt(h * h + (a / 2) ** 2)
    const m = Math.min(sa, sh) * 0.25

    return {
      // 4-sided cone with circumradius a/√2, rotated 45° → square base of side a.
      meshes: [{ kind: "cone", args: [sa / Math.SQRT2, sh, 4], rotation: [0, Math.PI / 4, 0], color: "#eab308", opacity: 0.25, edges: true }],
      labels: [{ text: `a = ${a} cm`, position: add(frontMid, [0, -0.5, 0.4]), kind: "dimension" }],
      constructionLabels: [
        { text: `h = ${h} cm`, position: add(scale(add(apex, baseC), 0.5), [-0.5, 0, 0]), kind: "dimension" },
        { text: `slant = ${slant.toFixed(2)} cm`, position: add(scale(add(apex, edgeMid), 0.5), [0.7, 0, 0]), kind: "angle" },
      ],
      constructionLines: [
        { points: [apex, baseC], color: "#a78bfa", width: 4 },
        { points: [baseC, edgeMid], color: "#22d3ee", width: 4 },
        { points: [apex, edgeMid], color: "#f97316", width: 5 },
        { points: [add(baseC, [0, m, 0]), add(baseC, [m, m, 0]), add(baseC, [m, 0, 0])], color: "#94a3b8", width: 2 },
      ],
      working: [
        { title: "Slant height = √(h² + (a⁄2)²)", detail: `= √(${h}² + ${(a / 2)}²) = ${slant.toFixed(2)} cm`, color: "#f97316" },
        { title: "Volume V = ⅓ a² h", detail: `= ⅓·${a}²·${h} = ${((a * a * h) / 3).toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Surface area = a² + 2a·(slant)", detail: `= ${(a * a + 2 * a * slant).toFixed(2)} cm²`, color: "#22d3ee" },
      ],
      // Net: base square + 4 triangular faces (triangle height = slant height).
      net: (() => {
        const ls = slant * k // slant height in scene units
        const triArea = areaLabel(0.5 * a * slant)
        const half = sa / 2
        return [
          face(rect(0, 0, sa, sa), "#ca8a04", areaLabel(a * a)),
          face(tri([-half, half], [half, half], [0, half + ls]), "#eab308", triArea),
          face(tri([-half, -half], [half, -half], [0, -half - ls]), "#eab308", triArea),
          face(tri([-half, -half], [-half, half], [-half - ls, 0]), "#facc15", triArea),
          face(tri([half, -half], [half, half], [half + ls, 0]), "#facc15", triArea),
        ]
      })(),
      metrics: { volume: (a * a * h) / 3, surfaceArea: a * a + 2 * a * slant },
    }
  },
}
