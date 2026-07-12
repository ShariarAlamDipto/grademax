// Rectangular-based right pyramid ABCDE (apex E over centre M), defined by the
// base AB × BC and the equal slant edges EA=EB=EC=ED — the exact form of the
// Edexcel "right pyramid" questions. Computes the perpendicular height, the two
// slant heights, total surface area, and ∠PEQ (P,Q = midpoints of AB,BC).

import type { ShapeTemplate, ShapeModel, Vec3, SceneLabel } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, sub, scale, norm, mid, arc } from "../core/vec"
import { rect, tri, face, areaLabel } from "../core/net"

export const rectpyramid: ShapeTemplate = {
  id: "rectpyramid",
  name: "Rectangular pyramid",
  keywords: ["pyramid"],
  params: [
    { key: "l", label: "Base AB", symbol: "AB", unit: "cm", default: 8, min: 0.1, step: 0.5 },
    { key: "w", label: "Base BC", symbol: "BC", unit: "cm", default: 10, min: 0.1, step: 0.5 },
    { key: "e", label: "Slant edge EA", symbol: "EA", unit: "cm", default: 12, min: 0.1, step: 0.5 },
  ],
  compute: ({ l, w, e }): ShapeModel => {
    const halfDiag = 0.5 * Math.sqrt(l * l + w * w) // M → corner
    const hReal = Math.sqrt(Math.max(e * e - halfDiag * halfDiag, 1e-6)) // perpendicular height EM
    const k = scaleFactor(Math.max(l, w, hReal))
    const sl = l * k, sw = w * k, sh = hReal * k
    const x = sl / 2, y = sh / 2, z = sw / 2

    const V: Record<string, Vec3> = {
      A: [-x, -y, -z], B: [x, -y, -z], C: [x, -y, z], D: [-x, -y, z],
      E: [0, y, 0], M: [0, -y, 0],
    }
    const { A, B, C, D, E, M } = V
    const P = mid(A, B) // midpoint AB
    const Q = mid(B, C) // midpoint BC

    const labels: SceneLabel[] = [
      { text: `AB = ${l} cm`, position: add(mid(A, B), [0, -0.4, -0.4]), kind: "dimension" },
      { text: `BC = ${w} cm`, position: add(mid(B, C), [0.5, -0.4, 0]), kind: "dimension" },
      { text: `EA = ${e} cm`, position: add(mid(E, B), [0.5, 0, -0.3]), kind: "dimension" },
      ...Object.entries(V).map(([name, p]) => ({
        text: name,
        position: name === "M" ? add(p, [0, 0.25, 0]) : scale(p, 1.12),
        kind: "vertex" as const,
      })),
    ]

    // Derived lengths
    const EM = hReal
    const EP = Math.sqrt(Math.max(e * e - (l / 2) ** 2, 0)) // slant height onto AB
    const EQ = Math.sqrt(Math.max(e * e - (w / 2) ** 2, 0)) // slant height onto BC
    const PQ = Math.sqrt((l / 2) ** 2 + (w / 2) ** 2)
    const cosPEQ = Math.min(1, Math.max(-1, (EP * EP + EQ * EQ - PQ * PQ) / (2 * EP * EQ)))
    const angPEQ = (Math.acos(cosPEQ) * 180) / Math.PI
    const sa = l * w + l * EP + w * EQ

    // ∠PEQ arc at E
    const r = Math.min(sl, sw, sh) * 0.45
    const arcPts = arc(E, sub(P, E), sub(Q, E), r)
    const angLabelPos = add(E, scale(norm(sub(arcPts[Math.floor(arcPts.length / 2)], E)), r * 1.6))
    const mk = Math.min(sl, sw) * 0.22

    return {
      meshes: [{ kind: "rectpyramid", args: [sl, sh, sw], color: "#eab308", opacity: 0.2, edges: true }],
      labels,
      constructionLabels: [
        { text: `EM = ${EM.toFixed(2)} cm`, position: add(mid(E, M), [-0.55, 0, 0]), kind: "dimension" },
        { text: `∠PEQ = ${angPEQ.toFixed(1)}°`, position: angLabelPos, kind: "angle" },
        { text: "P", position: add(P, [0, -0.25, -0.2]), kind: "vertex" },
        { text: "Q", position: add(Q, [0.25, -0.25, 0]), kind: "vertex" },
      ],
      constructionLines: [
        { points: [E, M], color: "#a78bfa", width: 4 }, // perpendicular height
        { points: [add(M, [0, mk, 0]), add(M, [mk, mk, 0]), add(M, [mk, 0, 0])], color: "#94a3b8", width: 2 },
        { points: [E, P], color: "#22d3ee", width: 4 },
        { points: [E, Q], color: "#22d3ee", width: 4 },
        { points: [P, Q], color: "#f97316", width: 4, dashed: true },
        { points: arcPts, color: "#facc15", width: 4 },
      ],
      working: [
        { title: "Perpendicular height EM = √(EA² − ¼(AB² + BC²))", detail: `= √(${e}² − ¼(${l}² + ${w}²)) = ${EM.toFixed(3)} cm`, color: "#a78bfa" },
        { title: "Slant height EP (onto AB) = √(EA² − (AB⁄2)²)", detail: `= √(${e}² − ${l / 2}²) = ${EP.toFixed(3)} cm`, color: "#22d3ee" },
        { title: "Slant height EQ (onto BC) = √(EA² − (BC⁄2)²)", detail: `= √(${e}² − ${w / 2}²) = ${EQ.toFixed(3)} cm`, color: "#22d3ee" },
        { title: "(a) Total surface area = AB·BC + AB·EP + BC·EQ", detail: `= ${(l * w).toFixed(0)} + ${(l * EP).toFixed(2)} + ${(w * EQ).toFixed(2)} = ${sa.toFixed(1)} ≈ ${sa.toPrecision(3)} cm²`, color: "#f97316" },
        { title: "(b) PQ = √((AB⁄2)² + (BC⁄2)²)", detail: `= √(${l / 2}² + ${w / 2}²) = ${PQ.toFixed(3)} cm`, color: "#facc15" },
        { title: "∠PEQ = cos⁻¹((EP² + EQ² − PQ²) ⁄ (2·EP·EQ))", detail: `= ${angPEQ.toFixed(1)}°`, color: "#facc15" },
        { title: "Volume V = ⅓ · AB · BC · EM", detail: `= ${((l * w * EM) / 3).toFixed(2)} cm³` },
      ],
      // Net: base rectangle + 4 triangles (front/back use EP, left/right use EQ).
      net: (() => {
        const epS = EP * k, eqS = EQ * k
        const hx = sl / 2, hz = sw / 2
        return [
          face(rect(0, 0, sl, sw), "#ca8a04", areaLabel(l * w)),
          face(tri([-hx, -hz], [hx, -hz], [0, -hz - epS]), "#eab308", areaLabel(0.5 * l * EP)),
          face(tri([-hx, hz], [hx, hz], [0, hz + epS]), "#eab308", areaLabel(0.5 * l * EP)),
          face(tri([-hx, -hz], [-hx, hz], [-hx - eqS, 0]), "#facc15", areaLabel(0.5 * w * EQ)),
          face(tri([hx, -hz], [hx, hz], [hx + eqS, 0]), "#facc15", areaLabel(0.5 * w * EQ)),
        ]
      })(),
      metrics: { volume: (l * w * EM) / 3, surfaceArea: sa },
    }
  },
}
