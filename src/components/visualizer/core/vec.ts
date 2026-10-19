// Tiny immutable Vec3 helpers shared by all shape templates. No three.js import,
// so shape geometry stays pure and unit-testable.

import type { Vec3 } from "./types"

export const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
export const add = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
export const scale = (a: Vec3, s: number): Vec3 => [a[0] * s, a[1] * s, a[2] * s]
export const dot = (a: Vec3, b: Vec3): number => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
export const len = (a: Vec3): number => Math.sqrt(dot(a, a))
export const mid = (a: Vec3, b: Vec3): Vec3 => scale(add(a, b), 0.5)
export const norm = (a: Vec3): Vec3 => {
  const l = len(a)
  return l < 1e-9 ? [0, 0, 0] : scale(a, 1 / l)
}

/** Spherical interpolation between two unit vectors — for angle arcs. */
export function slerp(a: Vec3, b: Vec3, t: number): Vec3 {
  const d = Math.max(-1, Math.min(1, dot(a, b)))
  const omega = Math.acos(d)
  if (omega < 1e-6) return a
  const so = Math.sin(omega)
  return add(scale(a, Math.sin((1 - t) * omega) / so), scale(b, Math.sin(t * omega) / so))
}

/** Sample an arc between two directions from a point — N+1 points. */
export function arc(origin: Vec3, dirA: Vec3, dirB: Vec3, radius: number, n = 24): Vec3[] {
  const a = norm(dirA)
  const b = norm(dirB)
  return Array.from({ length: n + 1 }, (_, i) => add(origin, scale(slerp(a, b, i / n), radius)))
}
