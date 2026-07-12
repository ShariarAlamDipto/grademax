// Volume of revolution (Further Pure / calculus). Revolves the curve y = f(x)
// about the x-axis between x = a and x = b. Builds a LatheGeometry from the
// profile and finds the volume by numerically integrating V = π∫ y² dx.

import type { ShapeTemplate, ShapeModel, Vec3 } from "../core/types"
import { scaleFactor } from "../core/types"

// Curve presets selectable via a dropdown param (value = index).
const CURVES: { label: string; f: (x: number) => number; expr: string }[] = [
  { label: "y = √x", f: (x) => Math.sqrt(Math.max(x, 0)), expr: "√x" },
  { label: "y = x (cone)", f: (x) => x, expr: "x" },
  { label: "y = x²", f: (x) => x * x, expr: "x²" },
  { label: "y = √(r²−x²) (sphere)", f: (x) => Math.sqrt(Math.max(4 - x * x, 0)), expr: "√(4 − x²)" },
]

const SAMPLES = 60

export const revolution: ShapeTemplate = {
  id: "revolution",
  name: "Volume of revolution",
  keywords: ["revolution", "revolve", "rotated about", "volume of revolution"],
  params: [
    { key: "curve", label: "Curve", symbol: "f", unit: "", default: 0, min: 0, step: 1, choices: CURVES.map((c, i) => ({ label: c.label, value: i })) },
    { key: "a", label: "Lower limit a", symbol: "a", unit: "", default: 0, min: -10, step: 0.5 },
    { key: "b", label: "Upper limit b", symbol: "b", unit: "", default: 4, min: 0.5, step: 0.5 },
  ],
  compute: ({ curve, a, b }): ShapeModel => {
    const c = CURVES[Math.max(0, Math.min(CURVES.length - 1, Math.round(curve)))]
    const lo = Math.min(a, b)
    const hi = Math.max(a, b, lo + 0.5)

    // Sample the profile and find the scale that fits it to the viewport.
    const xs = Array.from({ length: SAMPLES + 1 }, (_, i) => lo + ((hi - lo) * i) / SAMPLES)
    const ys = xs.map((x) => c.f(x))
    const maxY = Math.max(...ys, 1e-6)
    const k = scaleFactor(Math.max(hi - lo, 2 * maxY))

    // Numerical volume V = π ∫ y² dx (trapezium rule).
    let vol = 0
    for (let i = 0; i < SAMPLES; i++) {
      const y0 = ys[i], y1 = ys[i + 1]
      vol += ((y0 * y0 + y1 * y1) / 2) * ((hi - lo) / SAMPLES)
    }
    vol *= Math.PI

    // LatheGeometry revolves (radius, height) about the Y axis. We map the curve
    // so the revolution axis (x) runs along Y, radius = f(x). args = flat [r,h,…].
    const mid = (lo + hi) / 2
    const profile: number[] = []
    xs.forEach((x, i) => {
      profile.push(ys[i] * k, (x - mid) * k) // radius, height
    })

    // The mesh is rotated +90° about Z, which maps the lathe height axis to −X.
    // So the reference curve/axis/labels use X = −(x − mid)·k to overlay the solid.
    const X = (x: number) => -(x - mid) * k
    const curveLine: Vec3[] = xs.map((x, i) => [X(x), ys[i] * k, 0])
    const axis: Vec3[] = [[X(lo), 0, 0], [X(hi), 0, 0]]

    return {
      meshes: [{ kind: "lathe", args: profile, rotation: [0, 0, Math.PI / 2], color: "#8b5cf6", opacity: 0.3 }],
      labels: [
        { text: `a = ${lo}`, position: [X(lo), -0.5, 0], kind: "dimension" },
        { text: `b = ${hi}`, position: [X(hi), -0.5, 0], kind: "dimension" },
        { text: c.label, position: [0, maxY * k + 0.6, 0], kind: "dimension" },
      ],
      constructionLabels: [],
      constructionLines: [
        { points: axis, color: "#94a3b8", width: 2, dashed: true },
        { points: curveLine, color: "#f97316", width: 5 },
      ],
      working: [
        { title: `Curve y = ${c.expr}, revolved about the x-axis`, detail: `for ${lo} ≤ x ≤ ${hi}`, color: "#f97316" },
        { title: "Volume V = π ∫ y² dx", detail: `= π ∫ (${c.expr})² dx from ${lo} to ${hi}`, color: "#8b5cf6" },
        { title: "Numerical value", detail: `V ≈ ${vol.toFixed(3)} (≈ ${(vol / Math.PI).toFixed(3)} π)`, color: "#a78bfa" },
      ],
    }
  },
}
