// Frustum of a cone (a cone with the top sliced off parallel to the base).
// Rendered as a cylinder with unequal top/bottom radii.

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, scale } from "../core/vec"

export const frustum: ShapeTemplate = {
  id: "frustum",
  name: "Cone frustum",
  keywords: ["frustum", "bucket", "truncated cone", "lampshade"],
  params: [
    { key: "R", label: "Base radius", symbol: "R", unit: "cm", default: 6, min: 0.1, step: 0.5 },
    { key: "r", label: "Top radius", symbol: "r", unit: "cm", default: 3, min: 0.05, step: 0.5 },
    { key: "h", label: "Height", symbol: "h", unit: "cm", default: 8, min: 0.1, step: 0.5 },
  ],
  compute: ({ R, r, h }): ShapeModel => {
    const k = scaleFactor(Math.max(2 * R, h))
    const sR = R * k, sr = r * k, sh = h * k
    const topC: Vec3 = [0, sh / 2, 0]
    const botC: Vec3 = [0, -sh / 2, 0]
    const topRim: Vec3 = [sr, sh / 2, 0]
    const botRim: Vec3 = [sR, -sh / 2, 0]

    const slant = Math.sqrt(h * h + (R - r) ** 2)
    const vol = (Math.PI * h * (R * R + R * r + r * r)) / 3
    const curved = Math.PI * (R + r) * slant

    return {
      meshes: [{ kind: "cylinder", args: [sr, sR, sh, 64], color: "#0ea5e9", opacity: 0.22, edges: true }],
      labels: [
        { text: `R = ${R} cm`, position: add(scale(add(botC, botRim), 0.5), [0, -0.5, 0]), kind: "dimension" },
        { text: `r = ${r} cm`, position: add(scale(add(topC, topRim), 0.5), [0, 0.5, 0]), kind: "dimension" },
        { text: `h = ${h} cm`, position: add(scale(add(topC, botC), 0.5), [-0.55, 0, 0]), kind: "dimension" },
      ],
      constructionLabels: [{ text: `slant = ${slant.toFixed(2)} cm`, position: add(scale(add(topRim, botRim), 0.5), [0.6, 0, 0]), kind: "angle" }],
      constructionLines: [
        { points: [topC, botC], color: "#a78bfa", width: 4 },
        { points: [botC, botRim], color: "#22d3ee", width: 4 },
        { points: [topRim, botRim], color: "#f97316", width: 5 },
      ],
      working: [
        { title: "Slant height = √(h² + (R − r)²)", detail: `= √(${h}² + ${R - r}²) = ${slant.toFixed(2)} cm`, color: "#f97316" },
        { title: "Volume V = ⅓πh(R² + Rr + r²)", detail: `= ${vol.toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Curved surface = π(R + r)·slant", detail: `= ${curved.toFixed(2)} cm²`, color: "#22d3ee" },
        { title: "Total surface = curved + πR² + πr²", detail: `= ${(curved + Math.PI * R * R + Math.PI * r * r).toFixed(2)} cm²` },
      ],
      metrics: { volume: vol, surfaceArea: curved + Math.PI * R * R + Math.PI * r * r },
    }
  },
}
