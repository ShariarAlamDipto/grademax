// Helpers for building unfolded-net faces as flat 2D polygons in the (u, v)
// layout plane. Shapes compose these; the renderer lays them flat on the ground.

import type { NetFace } from "./types"

type P = [number, number]

/** Axis-aligned rectangle centred at (cx, cy). */
export function rect(cx: number, cy: number, w: number, h: number): P[] {
  const x = w / 2, y = h / 2
  return [[cx - x, cy - y], [cx + x, cy - y], [cx + x, cy + y], [cx - x, cy + y]]
}

/** Triangle from three explicit points. */
export function tri(a: P, b: P, c: P): P[] {
  return [a, b, c]
}

/** Regular polygon approximating a circle centred at (cx, cy). */
export function circlePoly(cx: number, cy: number, r: number, n = 40): P[] {
  return Array.from({ length: n }, (_, i) => {
    const t = (i / n) * Math.PI * 2
    return [cx + r * Math.cos(t), cy + r * Math.sin(t)] as P
  })
}

/** Circular sector: apex at (cx, cy), radius R, sweeping `angle` rad about `start`. */
export function sectorPoly(cx: number, cy: number, R: number, angle: number, start: number, n = 48): P[] {
  const pts: P[] = [[cx, cy]]
  for (let i = 0; i <= n; i++) {
    const t = start + (i / n) * angle
    pts.push([cx + R * Math.cos(t), cy + R * Math.sin(t)])
  }
  return pts
}

export function face(points: P[], color: string, label?: string, labelAt?: P): NetFace {
  return { points, color, label, labelAt }
}

/** Format an area for a face label. */
export const areaLabel = (n: number): string => `${+n.toFixed(2)} cm²`
