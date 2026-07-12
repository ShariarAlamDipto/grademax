"use client"

// Generic 3D viewport. Renders any ShapeModel (meshes + construction lines +
// labels) with orbit/rotate/zoom controls for the classroom projector.
// Labels are individually clickable to hide; restored from the control panel.

import { useMemo } from "react"
import * as THREE from "three"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Edges, Line, Html } from "@react-three/drei"
import type { ShapeModel, MeshSpec, SceneLabel, SceneLine, NetFace } from "./core/types"

export interface SceneToggles {
  showValues: boolean
  showVertices: boolean
  showConstruction: boolean
  showNet: boolean
}

/** Stable per-label key: the text before "=", so it survives value changes. */
export function labelKey(label: SceneLabel): string {
  return label.text.split("=")[0].trim()
}

const labelStyles: Record<SceneLabel["kind"], React.CSSProperties> = {
  dimension: { background: "rgba(15,23,42,0.9)", color: "#fff", fontSize: 16, fontWeight: 700, padding: "2px 8px" },
  vertex: { background: "transparent", color: "#67e8f9", fontSize: 18, fontWeight: 800, textShadow: "0 0 4px #000" },
  angle: { background: "rgba(250,204,21,0.95)", color: "#1a1a00", fontSize: 16, fontWeight: 800, padding: "2px 9px" },
}

function LabelTag({ label, onClick }: { label: SceneLabel; onClick?: () => void }) {
  return (
    <Html position={label.position} center distanceFactor={14} zIndexRange={[10, 0]}>
      <div
        title={onClick ? "Click to hide" : undefined}
        onClick={onClick ? (e) => { e.stopPropagation(); onClick() } : undefined}
        style={{
          ...labelStyles[label.kind],
          borderRadius: 6,
          whiteSpace: "nowrap",
          userSelect: "none",
          cursor: onClick ? "pointer" : "default",
          pointerEvents: onClick ? "auto" : "none",
        }}
      >
        {label.text}
      </div>
    </Html>
  )
}

function PolyLine({ line }: { line: SceneLine }) {
  return <Line points={line.points} color={line.color} lineWidth={line.width} dashed={!!line.dashed} dashSize={0.4} gapSize={0.25} />
}

/** Build a rectangular-pyramid BufferGeometry: 4 base corners + apex. */
function buildRectPyramid([sl, sh, sw]: number[]): THREE.BufferGeometry {
  const x = sl / 2, y = sh / 2, z = sw / 2
  const A = [-x, -y, -z], B = [x, -y, -z], C = [x, -y, z], D = [-x, -y, z], E = [0, y, 0]
  const tris = [...A, ...C, ...B, ...A, ...D, ...C, ...A, ...B, ...E, ...B, ...C, ...E, ...C, ...D, ...E, ...D, ...A, ...E]
  const g = new THREE.BufferGeometry()
  g.setAttribute("position", new THREE.Float32BufferAttribute(tris, 3))
  g.computeVertexNormals()
  return g
}

function centroid(points: [number, number][]): [number, number] {
  const n = points.length
  const s = points.reduce((a, p) => [a[0] + p[0], a[1] + p[1]], [0, 0])
  return [s[0] / n, s[1] / n]
}

/** One flat polygon face of an unfolded net, laid on the ground plane. */
function NetFaceMesh({ f }: { f: NetFace }) {
  const geom = useMemo(() => {
    const shape = new THREE.Shape()
    f.points.forEach(([x, y], i) => (i ? shape.lineTo(x, y) : shape.moveTo(x, y)))
    shape.closePath()
    return new THREE.ShapeGeometry(shape)
  }, [f])
  const [lx, ly] = f.labelAt ?? centroid(f.points)
  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      <mesh>
        <primitive object={geom} attach="geometry" />
        <meshStandardMaterial color={f.color} transparent opacity={0.35} side={THREE.DoubleSide} depthWrite={false} />
        <Edges color="#93c5fd" lineWidth={2} />
      </mesh>
      {f.label && (
        <Html position={[lx, ly, 0.02]} center distanceFactor={14} zIndexRange={[10, 0]}>
          <div style={{ background: "rgba(15,23,42,0.9)", color: "#fff", fontSize: 14, fontWeight: 700, padding: "2px 7px", borderRadius: 5, whiteSpace: "nowrap", pointerEvents: "none" }}>{f.label}</div>
        </Html>
      )}
    </group>
  )
}

/** Build a triangular prism ("tent"): triangle (base z, height y) extruded along x. */
function buildPrism([sb, sht, sL]: number[]): THREE.BufferGeometry {
  const hx = sL / 2, hy = sht / 2, hz = sb / 2
  const A = [hx, -hy, -hz], B = [hx, -hy, hz], C = [hx, hy, 0] // right end
  const D = [-hx, -hy, -hz], E = [-hx, -hy, hz], F = [-hx, hy, 0] // left end
  const tris = [
    ...A, ...B, ...C, // right triangle
    ...D, ...F, ...E, // left triangle
    ...A, ...B, ...E, ...A, ...E, ...D, // bottom base
    ...B, ...C, ...F, ...B, ...F, ...E, // slope (z+)
    ...A, ...C, ...F, ...A, ...F, ...D, // slope (z−)
  ]
  const g = new THREE.BufferGeometry()
  g.setAttribute("position", new THREE.Float32BufferAttribute(tris, 3))
  g.computeVertexNormals()
  return g
}

/** Build a LatheGeometry from a flat [radius, height, …] profile. */
function buildLathe(args: number[]): THREE.LatheGeometry {
  const pts: THREE.Vector2[] = []
  for (let i = 0; i + 1 < args.length; i += 2) pts.push(new THREE.Vector2(Math.max(args[i], 0), args[i + 1]))
  return new THREE.LatheGeometry(pts, 64)
}

/** Build a flat ShapeGeometry (XY plane) from a closed [x, y, …] polygon. */
function buildPolygon2D(args: number[]): THREE.ShapeGeometry {
  const shape = new THREE.Shape()
  for (let i = 0; i + 1 < args.length; i += 2) (i ? shape.lineTo(args[i], args[i + 1]) : shape.moveTo(args[i], args[i + 1]))
  shape.closePath()
  return new THREE.ShapeGeometry(shape)
}

function ShapeMesh({ m, opacityScale = 1 }: { m: MeshSpec; opacityScale?: number }) {
  const pyramidGeom = useMemo(() => (m.kind === "rectpyramid" ? buildRectPyramid(m.args) : null), [m])
  const prismGeom = useMemo(() => (m.kind === "prism" ? buildPrism(m.args) : null), [m])
  const latheGeom = useMemo(() => (m.kind === "lathe" ? buildLathe(m.args) : null), [m])
  const polyGeom = useMemo(() => (m.kind === "polygon2d" ? buildPolygon2D(m.args) : null), [m])
  const custom = m.kind === "rectpyramid" || m.kind === "prism" || m.kind === "lathe" || m.kind === "polygon2d"
  return (
    <mesh position={m.position ?? [0, 0, 0]} rotation={m.rotation ?? [0, 0, 0]}>
      {m.kind === "box" && <boxGeometry args={m.args as [number, number, number]} />}
      {m.kind === "cone" && <coneGeometry args={m.args as [number, number, number]} />}
      {m.kind === "cylinder" && <cylinderGeometry args={m.args as [number, number, number, number]} />}
      {m.kind === "sphere" && <sphereGeometry args={m.args as [number, number, number, number?, number?, number?, number?]} />}
      {pyramidGeom && <primitive object={pyramidGeom} attach="geometry" />}
      {prismGeom && <primitive object={prismGeom} attach="geometry" />}
      {latheGeom && <primitive object={latheGeom} attach="geometry" />}
      {polyGeom && <primitive object={polyGeom} attach="geometry" />}
      <meshStandardMaterial color={m.color ?? "#1d4ed8"} transparent opacity={(m.opacity ?? 0.2) * opacityScale} depthWrite={false} side={custom ? THREE.DoubleSide : THREE.FrontSide} />
      {m.edges && <Edges color="#93c5fd" lineWidth={2.5} />}
    </mesh>
  )
}

interface SceneProps {
  model: ShapeModel
  toggles: SceneToggles
  hidden: Set<string>
  onHideLabel: (key: string) => void
  enlargeK: number
}

function CompareTag({ text, position, color }: { text: string; position: [number, number, number]; color: string }) {
  return (
    <Html position={position} center distanceFactor={14} zIndexRange={[10, 0]}>
      <div style={{ background: color, color: "#0b1220", fontSize: 15, fontWeight: 800, padding: "2px 9px", borderRadius: 6, whiteSpace: "nowrap", pointerEvents: "none" }}>{text}</div>
    </Html>
  )
}

export default function Scene({ model, toggles, hidden, onHideLabel, enlargeK }: SceneProps) {
  const renderLabel = (label: SceneLabel, fallbackKey: string) => {
    const key = labelKey(label) || fallbackKey
    if (hidden.has(key)) return null
    return <LabelTag key={fallbackKey} label={label} onClick={() => onHideLabel(key)} />
  }

  const netMode = toggles.showNet && !!model.net
  const compareMode = !netMode && enlargeK > 1.0001

  return (
    <Canvas camera={{ position: [9, 7, 12], fov: 45 }} style={{ background: "#0b1220" }}>
      <ambientLight intensity={0.75} />
      <directionalLight position={[8, 12, 6]} intensity={1.1} />
      <directionalLight position={[-6, 4, -8]} intensity={0.4} />

      {netMode && model.net!.map((f, i) => <NetFaceMesh key={`n${i}`} f={f} />)}

      {compareMode && (
        <>
          <group position={[-4, 0, 0]}>
            {model.meshes.map((m, i) => <ShapeMesh key={`o${i}`} m={m} />)}
          </group>
          <CompareTag text="×1" position={[-4, -4, 0]} color="#93c5fd" />
          <group position={[4.5, 0, 0]} scale={enlargeK}>
            {model.meshes.map((m, i) => <ShapeMesh key={`e${i}`} m={m} opacityScale={1.4} />)}
          </group>
          <CompareTag text={`×${(+enlargeK.toFixed(2))}`} position={[4.5, -4, 0]} color="#fcd34d" />
        </>
      )}

      {!netMode && !compareMode && (
        <>
          {model.meshes.map((m, i) => <ShapeMesh key={`m${i}`} m={m} />)}

          {toggles.showConstruction && (
            <>
              {model.constructionLines.map((l, i) => <PolyLine key={`c${i}`} line={l} />)}
              {model.constructionLabels.map((l, i) => renderLabel(l, `cl${i}`))}
            </>
          )}

          {model.labels.map((l, i) => {
            if (l.kind === "dimension" && !toggles.showValues) return null
            if (l.kind === "vertex" && !toggles.showVertices) return null
            return renderLabel(l, `l${i}`)
          })}
        </>
      )}

      <OrbitControls enableDamping makeDefault />
    </Canvas>
  )
}
