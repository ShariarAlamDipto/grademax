// Core type contract for the Maths Visualizer "smart shape" engine.
// Every shape template conforms to ShapeTemplate so the renderer, control panel
// and import pipeline all stay generic: input → params → meshes + labels + moves.

export type Vec3 = [number, number, number]

export type ShapeId =
  | "cuboid"
  | "cone"
  | "cylinder"
  | "sphere"
  | "hemisphere"
  | "pyramid"
  | "rectpyramid"
  | "prism"
  | "frustum"
  | "revolution"
  | "graph"
  | "areaundercurve"

/** A single teacher-editable parameter, e.g. the radius of a cone. */
export interface ParamSpec {
  key: string
  label: string
  /** Maths symbol shown on the diagram, e.g. "r". */
  symbol: string
  unit: string
  default: number
  min: number
  step: number
  /** If present, the control renders a dropdown of these numeric choices. */
  choices?: { label: string; value: number }[]
}

export interface SceneLabel {
  text: string
  position: Vec3
  kind: "dimension" | "vertex" | "angle"
}

export interface SceneLine {
  points: Vec3[]
  color: string
  /** Pixel width — kept chunky for projector visibility. */
  width: number
  dashed?: boolean
}

/** A primitive mesh the generic renderer knows how to draw. */
export interface MeshSpec {
  kind: "box" | "cone" | "cylinder" | "sphere" | "rectpyramid" | "prism" | "lathe" | "polygon2d"
  /** three.js geometry args for the matching primitive. */
  args: number[]
  position?: Vec3
  /** Euler rotation in radians. */
  rotation?: Vec3
  color?: string
  opacity?: number
  edges?: boolean
}

/** One line of the "show working" panel. */
export interface WorkingStep {
  title: string
  detail: string
  color?: string
}

/** One flat face of an unfolded net: a closed polygon in the 2D (u, v) plane. */
export interface NetFace {
  /** Polygon vertices in order, in the net's (u, v) layout plane. */
  points: [number, number][]
  color: string
  label?: string
  /** Where to anchor the label; defaults to the vertex centroid. */
  labelAt?: [number, number]
}

/** Everything the renderer needs to draw one shape. */
export interface ShapeModel {
  meshes: MeshSpec[]
  /** Dimension + vertex labels (toggle: Labels). */
  labels: SceneLabel[]
  /** Construction labels — angles, slant heights (toggle: Construction). */
  constructionLabels: SceneLabel[]
  constructionLines: SceneLine[]
  working: WorkingStep[]
  /** Optional unfolded net (toggle: Net) — present only for shapes that have one. */
  net?: NetFace[]
  /** Real (unscaled) volume & surface area — powers the similar-solids feature. */
  metrics?: { volume: number; surfaceArea: number }
}

export interface ShapeTemplate {
  id: ShapeId
  name: string
  params: ParamSpec[]
  compute: (values: Record<string, number>) => ShapeModel
  /** Lowercase keywords the import extractor uses to recognise this shape. */
  keywords: string[]
}

/** Largest dimension maps to this scene size so any cm values fit the viewport. */
export const VIEW = 6

export function scaleFactor(maxDim: number): number {
  return VIEW / Math.max(maxDim, 1e-6)
}
