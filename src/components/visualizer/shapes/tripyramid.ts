// Triangular-based right pyramid DABC: an equilateral base ABC of side a with
// the apex D directly above the base centre M at perpendicular height h. Gives
// the two angles Edexcel asks for — face-to-base (∠DNM) and edge-to-base (∠DAM)
// — plus the slant height, slant edge, volume and surface area.
// A regular tetrahedron is just the case h = a√(2⁄3), e.g. a = 6, h = 4.9.

import type { ShapeTemplate, ShapeModel, Vec3, SceneLabel } from "../core/types"
import { scaleFactor } from "../core/types"
import { add, sub, scale, norm, mid, arc } from "../core/vec"
import { tri, face, areaLabel } from "../core/net"

const ROOT3 = Math.sqrt(3)

type P = [number, number]

/** Fold a lateral face out from base edge p→q, apex `ls` beyond the edge midpoint. */
function foldOut(p: P, q: P, ls: number): P[] {
  const m: P = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]
  const d = Math.hypot(m[0], m[1]) || 1 // base is centred on the origin, so m points outward
  return tri(p, q, [m[0] + (ls * m[0]) / d, m[1] + (ls * m[1]) / d])
}

export const tripyramid: ShapeTemplate = {
  id: "tripyramid",
  name: "Triangular pyramid",
  keywords: ["triangular pyramid", "triangular-based", "triangular based", "triangle based", "tetrahedron"],
  params: [
    { key: "a", label: "Base edge", symbol: "a", unit: "cm", default: 6, min: 0.1, step: 0.5 },
    { key: "h", label: "Height", symbol: "h", unit: "cm", default: 8, min: 0.1, step: 0.5 },
  ],
  compute: ({ a, h }): ShapeModel => {
    const k = scaleFactor(Math.max(a, h))
    const sa = a * k, sh = h * k
    const sR = sa / ROOT3 // base circumradius, scene units
    const y = sh / 2

    // Base vertices match three.js ConeGeometry(R, h, 3), which places them at
    // x = R sinθ, z = R cosθ for θ = 0, 2π⁄3, 4π⁄3 — so A sits at the front and
    // BC is the back edge, square-on to the camera.
    const V: Record<string, Vec3> = {
      A: [0, -y, sR],
      B: [(sR * ROOT3) / 2, -y, -sR / 2],
      C: [-(sR * ROOT3) / 2, -y, -sR / 2],
      D: [0, y, 0],
      M: [0, -y, 0],
    }
    const { A, B, D, M } = V
    const N = mid(V.B, V.C) // foot of the slant height on the back edge

    // Derived real lengths
    const inr = a / (2 * ROOT3) // base inradius, M → N
    const cir = a / ROOT3 // base circumradius, M → A
    const DN = Math.hypot(h, inr) // slant height (height of a lateral face)
    const DA = Math.hypot(h, cir) // slant edge
    const baseArea = (ROOT3 / 4) * a * a
    const lateral = 1.5 * a * DN
    const vol = (baseArea * h) / 3
    const angFace = (Math.atan2(h, inr) * 180) / Math.PI // face DBC to base
    const angEdge = (Math.atan2(h, cir) * 180) / Math.PI // edge DA to base

    const labels: SceneLabel[] = [
      { text: `a = ${a} cm`, position: add(mid(A, B), [0.45, -0.35, 0.3]), kind: "dimension" },
      ...Object.entries(V).map(([name, p]) => ({
        text: name,
        position: name === "M" ? add(p, [0, 0.3, 0]) : scale(p, 1.14),
        kind: "vertex" as const,
      })),
    ]

    // Angle arcs: at N between the slant height and the base, at A between the
    // slant edge and the base. Both arcs live in the x = 0 plane, so their
    // labels get pushed apart sideways or they overlap on screen.
    const rArc = Math.min(sa, sh) * 0.3
    const arcN = arc(N, sub(D, N), sub(M, N), rArc)
    const arcA = arc(A, sub(D, A), sub(M, A), rArc)
    const angPos = (v: Vec3, pts: Vec3[], nudge: Vec3): Vec3 =>
      add(add(v, scale(norm(sub(pts[Math.floor(pts.length / 2)], v)), rArc * 1.35)), nudge)
    const m = Math.min(sa, sh) * 0.16 // right-angle marker size

    return {
      // 3-sided cone with circumradius a⁄√3 → equilateral base of side a.
      meshes: [{ kind: "cone", args: [sR, sh, 3], color: "#eab308", opacity: 0.22, edges: true }],
      labels,
      constructionLabels: [
        { text: `h = ${h} cm`, position: add(mid(D, M), [-0.6, 0, 0]), kind: "dimension" },
        // Sits high on the slant line — the midpoint collides with the ∠DNM arc
        // once the pyramid is squat (small h, wide base).
        { text: `DN = ${DN.toFixed(2)} cm`, position: add(add(D, scale(sub(N, D), 0.42)), [1.15, 0.15, -0.15]), kind: "dimension" },
        { text: `∠DNM = ${angFace.toFixed(1)}°`, position: angPos(N, arcN, [1.15, 0.4, -1.2]), kind: "angle" },
        { text: `∠DAM = ${angEdge.toFixed(1)}°`, position: angPos(A, arcA, [-1.15, -0.55, 0.7]), kind: "angle" },
        { text: "N", position: add(N, [0, -0.3, -0.25]), kind: "vertex" },
      ],
      constructionLines: [
        { points: [D, M], color: "#a78bfa", width: 4 }, // perpendicular height
        { points: [add(M, [0, m, 0]), add(M, [0, m, -m]), add(M, [0, 0, -m])], color: "#94a3b8", width: 2 },
        { points: [M, N], color: "#22d3ee", width: 4 }, // base inradius
        { points: [D, N], color: "#f97316", width: 5 }, // slant height
        { points: [A, M], color: "#94a3b8", width: 3, dashed: true }, // base circumradius
        { points: arcN, color: "#facc15", width: 4 },
        { points: arcA, color: "#facc15", width: 4 },
      ],
      working: [
        { title: "Base area = (√3⁄4)a²", detail: `= (√3⁄4)·${a}² = ${baseArea.toFixed(2)} cm²`, color: "#ca8a04" },
        { title: "Slant height DN = √(h² + (a⁄(2√3))²)", detail: `= √(${h}² + ${inr.toFixed(3)}²) = ${DN.toFixed(3)} cm`, color: "#f97316" },
        { title: "Slant edge DA = √(h² + (a⁄√3)²)", detail: `= √(${h}² + ${cir.toFixed(3)}²) = ${DA.toFixed(3)} cm`, color: "#22d3ee" },
        { title: "Volume V = ⅓ × base area × h", detail: `= ⅓·${baseArea.toFixed(2)}·${h} = ${vol.toFixed(2)} cm³`, color: "#a78bfa" },
        { title: "Surface area = base + 3 × ½·a·DN", detail: `= ${baseArea.toFixed(2)} + ${lateral.toFixed(2)} = ${(baseArea + lateral).toFixed(2)} cm²` },
        { title: "Angle face DBC / base = tan⁻¹(h ÷ MN)", detail: `= tan⁻¹(${h} ÷ ${inr.toFixed(3)}) = ${angFace.toFixed(1)}°`, color: "#facc15" },
        { title: "Angle edge DA / base = tan⁻¹(h ÷ MA)", detail: `= tan⁻¹(${h} ÷ ${cir.toFixed(3)}) = ${angEdge.toFixed(1)}°`, color: "#facc15" },
      ],
      // Net: equilateral base + 3 identical triangles folded out on each edge
      // (triangle height = the slant height DN).
      net: (() => {
        const ls = DN * k
        const pA: P = [0, sR]
        const pB: P = [(sR * ROOT3) / 2, -sR / 2]
        const pC: P = [-(sR * ROOT3) / 2, -sR / 2]
        const faceArea = areaLabel(0.5 * a * DN)
        return [
          face(tri(pA, pB, pC), "#ca8a04", areaLabel(baseArea)),
          face(foldOut(pB, pC, ls), "#eab308", faceArea),
          face(foldOut(pA, pB, ls), "#facc15", faceArea),
          face(foldOut(pC, pA, ls), "#eab308", faceArea),
        ]
      })(),
      metrics: { volume: vol, surfaceArea: baseArea + lateral },
    }
  },
}
