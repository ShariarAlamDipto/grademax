// Triangular prism — an isosceles triangular cross-section (base b, height ht)
// extruded along its length L. The cross-section is constant, which is the key
// idea: Volume = (area of triangle) × length.

import type { ShapeTemplate, ShapeModel, Vec3, SceneLabel } from "../core/types"
import { scaleFactor } from "../core/types"
import { add } from "../core/vec"
import { rect, tri, face, areaLabel } from "../core/net"

export const prism: ShapeTemplate = {
  id: "prism",
  name: "Triangular prism",
  keywords: ["prism", "triangular prism", "toblerone"],
  params: [
    { key: "b", label: "Triangle base", symbol: "b", unit: "cm", default: 8, min: 0.1, step: 0.5 },
    { key: "ht", label: "Triangle height", symbol: "h", unit: "cm", default: 6, min: 0.1, step: 0.5 },
    { key: "L", label: "Prism length", symbol: "L", unit: "cm", default: 12, min: 0.1, step: 0.5 },
  ],
  compute: ({ b, ht, L }): ShapeModel => {
    const k = scaleFactor(Math.max(b, ht, L))
    const sb = b * k, sht = ht * k, sL = L * k
    // Length runs along x (horizontal); triangle base along z, height along y —
    // the classic "tent / Toblerone" lying on its rectangular base.
    const hx = sL / 2, hy = sht / 2, hz = sb / 2

    const A: Vec3 = [hx, -hy, -hz], B: Vec3 = [hx, -hy, hz], C: Vec3 = [hx, hy, 0] // right end
    const baseMid: Vec3 = [hx, -hy, 0] // midpoint of the right-end base edge

    const slant = Math.sqrt((b / 2) ** 2 + ht * ht)
    const triArea = 0.5 * b * ht
    const vol = triArea * L
    const sa = b * ht + (b + 2 * slant) * L
    const m = Math.min(sb, sht) * 0.22

    const labels: SceneLabel[] = [
      { text: `b = ${b} cm`, position: add(B, [0.3, -0.4, 0.3]), kind: "dimension" }, // end base width
      { text: `L = ${L} cm`, position: add([0, -hy, hz], [0, -0.4, 0.4]), kind: "dimension" }, // length along x
    ]

    return {
      meshes: [{ kind: "prism", args: [sb, sht, sL], color: "#14b8a6", opacity: 0.2, edges: true }],
      labels,
      constructionLabels: [{ text: `h = ${ht} cm`, position: add([hx, 0, 0], [0.5, 0, 0]), kind: "dimension" }],
      constructionLines: [
        { points: [baseMid, C], color: "#a78bfa", width: 4 }, // triangle perpendicular height at the end
        { points: [add(baseMid, [0, 0, m]), add(baseMid, [0, m, m]), add(baseMid, [0, m, 0])], color: "#94a3b8", width: 2 },
      ],
      working: [
        { title: "Cross-section area = ½ × b × h", detail: `= ½ × ${b} × ${ht} = ${triArea.toFixed(2)} cm²`, color: "#a78bfa" },
        { title: "Volume = cross-section × length", detail: `= ${triArea.toFixed(2)} × ${L} = ${vol.toFixed(2)} cm³`, color: "#22d3ee" },
        { title: "Sloped edge = √((b⁄2)² + h²)", detail: `= ${slant.toFixed(2)} cm`, color: "#f97316" },
        { title: "Surface area = b·h + (b + 2·slant)·L", detail: `= ${sa.toFixed(2)} cm²` },
      ],
      net: (() => {
        const slantS = slant * k
        return [
          face(rect(0, 0, sb, sL), "#0d9488", areaLabel(b * L)), // base rectangle
          face(rect(-(sb + slantS) / 2, 0, slantS, sL), "#14b8a6", areaLabel(slant * L)), // left slope
          face(rect((sb + slantS) / 2, 0, slantS, sL), "#14b8a6", areaLabel(slant * L)), // right slope
          face(tri([-sb / 2, sL / 2], [sb / 2, sL / 2], [0, sL / 2 + sht]), "#2dd4bf", areaLabel(triArea)),
          face(tri([-sb / 2, -sL / 2], [sb / 2, -sL / 2], [0, -sL / 2 - sht]), "#2dd4bf", areaLabel(triArea)),
        ]
      })(),
      metrics: { volume: vol, surfaceArea: sa },
    }
  },
}
