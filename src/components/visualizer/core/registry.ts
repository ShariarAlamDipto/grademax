// Shape registry. Add a shape = import it and add one entry here.

import type { ShapeId, ShapeTemplate } from "./types"
import { cuboid } from "../shapes/cuboid"
import { cone } from "../shapes/cone"
import { cylinder } from "../shapes/cylinder"
import { sphere } from "../shapes/sphere"
import { hemisphere } from "../shapes/hemisphere"
import { pyramid } from "../shapes/pyramid"
import { rectpyramid } from "../shapes/rectpyramid"
import { prism } from "../shapes/prism"
import { frustum } from "../shapes/frustum"
import { revolution } from "../shapes/revolution"
import { graph } from "../shapes/graph"
import { area } from "../shapes/area"

// Order matters for the picker AND for keyword tie-breaks (earlier wins ties):
// "square pyramid" must resolve before the generic rectangular pyramid.
export const shapeList: ShapeTemplate[] = [
  cuboid,
  cone,
  cylinder,
  sphere,
  hemisphere,
  pyramid,
  rectpyramid,
  prism,
  frustum,
  revolution,
  graph,
  area,
]

export const shapes: Record<ShapeId, ShapeTemplate> = {
  cuboid,
  cone,
  cylinder,
  sphere,
  hemisphere,
  pyramid,
  rectpyramid,
  prism,
  frustum,
  revolution,
  graph,
  areaundercurve: area,
}

/** Default param values for a shape, e.g. when switching shapes in the picker. */
export function defaultsFor(id: ShapeId): Record<string, number> {
  return Object.fromEntries(shapes[id].params.map((p) => [p.key, p.default]))
}
