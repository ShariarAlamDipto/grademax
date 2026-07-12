// Hemisphere template (top half of a sphere; flat circular base).

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"

export const hemisphere: ShapeTemplate = {
  id: "hemisphere",
  name: "Hemisphere",
  keywords: ["hemisphere", "half sphere", "half-sphere", "dome", "bowl"],
  params: [{ key: "r", label: "Radius", symbol: "r", unit: "cm", default: 6, min: 0.1, step: 0.5 }],
  compute: ({ r }): ShapeModel => {
    const k = scaleFactor(2 * r)
    const sr = r * k
    const center: Vec3 = [0, 0, 0]
    const edge: Vec3 = [sr, 0, 0]

    return {
      meshes: [
        // Upper hemisphere: thetaLength = π/2.
        { kind: "sphere", args: [sr, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2], color: "#f43f5e", opacity: 0.25, edges: true },
        // Thin disc closing the flat base, drawn as a near-flat cylinder.
        { kind: "cylinder", args: [sr, sr, 0.02, 48], color: "#f43f5e", opacity: 0.25 },
      ],
      labels: [{ text: `r = ${r} cm`, position: [sr / 2, 0.4, 0], kind: "dimension" }],
      constructionLabels: [],
      constructionLines: [{ points: [center, edge], color: "#22d3ee", width: 4 }],
      working: [
        { title: "Volume V = ⅔ πr³", detail: `= ⅔·π·${r}³ = ${((2 / 3) * Math.PI * r ** 3).toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Curved surface = 2πr²", detail: `= ${(2 * Math.PI * r * r).toFixed(2)} cm²`, color: "#22d3ee" },
        { title: "Total surface = 3πr² (curved + base circle)", detail: `= ${(3 * Math.PI * r * r).toFixed(2)} cm²` },
      ],
      metrics: { volume: (2 / 3) * Math.PI * r ** 3, surfaceArea: 3 * Math.PI * r * r },
    }
  },
}
