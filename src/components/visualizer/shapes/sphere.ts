// Sphere template.

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"

export const sphere: ShapeTemplate = {
  id: "sphere",
  name: "Sphere",
  keywords: ["sphere", "spherical", "ball", "globe"],
  params: [{ key: "r", label: "Radius", symbol: "r", unit: "cm", default: 5, min: 0.1, step: 0.5 }],
  compute: ({ r }): ShapeModel => {
    const k = scaleFactor(2 * r)
    const sr = r * k
    const center: Vec3 = [0, 0, 0]
    const edge: Vec3 = [sr, 0, 0]

    return {
      meshes: [{ kind: "sphere", args: [sr, 48, 32], color: "#f43f5e", opacity: 0.25, edges: false }],
      labels: [{ text: `r = ${r} cm`, position: [sr / 2, 0.4, 0], kind: "dimension" }],
      constructionLabels: [],
      constructionLines: [{ points: [center, edge], color: "#22d3ee", width: 4 }],
      working: [
        { title: "Volume V = 4⁄3 πr³", detail: `= 4⁄3·π·${r}³ = ${((4 / 3) * Math.PI * r ** 3).toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Surface area = 4πr²", detail: `= 4·π·${r}² = ${(4 * Math.PI * r * r).toFixed(2)} cm²`, color: "#22d3ee" },
      ],
      metrics: { volume: (4 / 3) * Math.PI * r ** 3, surfaceArea: 4 * Math.PI * r * r },
    }
  },
}
