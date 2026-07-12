// Cuboid template. Special construction: the angle between space diagonal AG
// and the base plane ABCD (the canonical IGCSE 3D-trig question).

import type { ShapeTemplate, ShapeModel, Vec3, SceneLabel, NetFace } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, sub, scale, norm, mid, arc } from "../core/vec"
import { rect, face, areaLabel } from "../core/net"

export const cuboid: ShapeTemplate = {
  id: "cuboid",
  name: "Cuboid",
  keywords: ["cuboid", "box", "block", "brick"],
  params: [
    { key: "l", label: "Length", symbol: "l", unit: "cm", default: 8, min: 0.1, step: 0.5 },
    { key: "w", label: "Width", symbol: "w", unit: "cm", default: 6, min: 0.1, step: 0.5 },
    { key: "h", label: "Height", symbol: "h", unit: "cm", default: 5, min: 0.1, step: 0.5 },
  ],
  compute: ({ l, w, h }): ShapeModel => {
    const k = scaleFactor(Math.max(l, w, h))
    const sl = l * k, sh = h * k, sw = w * k
    const x = sl / 2, y = sh / 2, z = sw / 2

    const V: Record<string, Vec3> = {
      A: [-x, -y, -z], B: [x, -y, -z], C: [x, -y, z], D: [-x, -y, z],
      E: [-x, y, -z], F: [x, y, -z], G: [x, y, z], H: [-x, y, z],
    }
    const { A, B, C, F, G } = V

    const labels: SceneLabel[] = [
      { text: `l = ${l} cm`, position: add(mid(A, B), [0, -0.5, -0.5]), kind: "dimension" },
      { text: `w = ${w} cm`, position: add(mid(B, C), [0.5, -0.5, 0]), kind: "dimension" },
      { text: `h = ${h} cm`, position: add(mid(B, F), [0.6, 0, -0.4]), kind: "dimension" },
      ...Object.entries(V).map(([name, p]) => ({ text: name, position: scale(p, 1.13), kind: "vertex" as const })),
    ]

    const baseDiag = Math.sqrt(l * l + w * w)
    const spaceDiag = Math.sqrt(l * l + w * w + h * h)
    const deg = (Math.atan2(h, baseDiag) * 180) / Math.PI

    const r = Math.min(sl, sw, sh) * 0.6
    const arcPts = arc(A, sub(C, A), sub(G, A), r)
    const midPt = arcPts[Math.floor(arcPts.length / 2)]
    const angleLabelPos = add(A, scale(norm(sub(midPt, A)), r * 1.5))
    const m = Math.min(sl, sw, sh) * 0.28
    const up: Vec3 = [0, 1, 0]
    const dirCA = norm(sub(A, C))

    // Unfolded net: a cross of the 6 faces, each labelled with its area.
    const net: NetFace[] = [
      face(rect(0, 0, sl, sh), "#1d4ed8", areaLabel(l * h)), // front
      face(rect(0, (sh + sw) / 2, sl, sw), "#2563eb", areaLabel(l * w)), // top
      face(rect(0, -(sh + sw) / 2, sl, sw), "#2563eb", areaLabel(l * w)), // bottom
      face(rect(0, sh + sw, sl, sh), "#1d4ed8", areaLabel(l * h)), // back
      face(rect(-(sl + sw) / 2, 0, sw, sh), "#3b82f6", areaLabel(w * h)), // left
      face(rect((sl + sw) / 2, 0, sw, sh), "#3b82f6", areaLabel(w * h)), // right
    ]

    return {
      meshes: [{ kind: "box", args: [sl, sh, sw], color: "#1d4ed8", opacity: 0.18, edges: true }],
      labels,
      constructionLabels: [
        { text: `θ = ${deg.toFixed(1)}°`, position: angleLabelPos, kind: "angle" },
      ],
      constructionLines: [
        { points: [A, C], color: "#22d3ee", width: 4, dashed: true },
        { points: [C, G], color: "#a78bfa", width: 4 },
        { points: [A, G], color: "#f97316", width: 5 },
        { points: arcPts, color: "#facc15", width: 4 },
        { points: [add(C, scale(dirCA, m)), add(add(C, scale(dirCA, m)), scale(up, m)), add(C, scale(up, m))], color: "#94a3b8", width: 2 },
      ],
      working: [
        { title: "Base diagonal AC = √(l² + w²)", detail: `= √(${l}² + ${w}²) = ${baseDiag.toFixed(2)} cm`, color: "#22d3ee" },
        { title: "Space diagonal AG = √(l² + w² + h²)", detail: `= ${spaceDiag.toFixed(2)} cm`, color: "#a78bfa" },
        { title: "Angle θ = tan⁻¹(h ÷ AC)", detail: `= tan⁻¹(${h} ÷ ${baseDiag.toFixed(2)}) = ${deg.toFixed(1)}°`, color: "#facc15" },
        { title: "Volume V = l × w × h", detail: `= ${(l * w * h).toFixed(2)} cm³` },
        { title: "Surface area = 2(lw + wh + lh)", detail: `= ${(2 * (l * w + w * h + l * h)).toFixed(2)} cm²` },
      ],
      net,
      metrics: { volume: l * w * h, surfaceArea: 2 * (l * w + w * h + l * h) },
    }
  },
}
