"use client"

// App shell: holds shape + values + toggles, recomputes the model, and lays out
// the control panel beside the 3D viewport. Client-only (WebGL).

import { useMemo, useState } from "react"
import ControlPanel from "./ControlPanel"
import Scene, { type SceneToggles } from "./Scene"
import ImportDropzone from "./ImportDropzone"
import { shapes, defaultsFor } from "./core/registry"
import type { ShapeId } from "./core/types"

export default function VisualizerApp() {
  const [shapeId, setShapeId] = useState<ShapeId>("rectpyramid")
  const [values, setValues] = useState<Record<string, number>>(() => defaultsFor("rectpyramid"))
  const [toggles, setToggles] = useState<SceneToggles>({ showValues: true, showVertices: true, showConstruction: true, showNet: false })
  const [showWorking, setShowWorking] = useState(true)
  const [importing, setImporting] = useState(false)
  const [hidden, setHidden] = useState<Set<string>>(() => new Set())
  const [enlargeK, setEnlargeK] = useState(1)
  const [sourceImage, setSourceImage] = useState<string | null>(null)

  const model = useMemo(() => shapes[shapeId].compute(values), [shapeId, values])

  const switchShape = (id: ShapeId) => {
    setShapeId(id)
    setValues(defaultsFor(id))
    setHidden(new Set()) // different labels per shape — start fresh
    setEnlargeK(1) // don't carry an enlargement onto a non-solid (e.g. graph)
  }

  const hideLabel = (key: string) => setHidden((h) => new Set(h).add(key))
  const restoreLabel = (key: string) =>
    setHidden((h) => {
      const next = new Set(h)
      next.delete(key)
      return next
    })

  return (
    <div style={{ display: "flex", height: "100vh", width: "100%", overflow: "hidden" }}>
      <ControlPanel
        shapeId={shapeId}
        onShape={switchShape}
        values={values}
        onValue={(key, n) => setValues((v) => ({ ...v, [key]: n }))}
        toggles={toggles}
        onToggle={(key) => setToggles((t) => ({ ...t, [key]: !t[key] }))}
        showWorking={showWorking}
        onShowWorking={() => setShowWorking((s) => !s)}
        model={model}
        onImport={() => setImporting(true)}
        hidden={hidden}
        onRestoreLabel={restoreLabel}
        onRestoreAll={() => setHidden(new Set())}
        enlargeK={enlargeK}
        onEnlargeK={setEnlargeK}
      />

      <div style={{ flex: 1, position: "relative" }}>
        <Scene model={model} toggles={toggles} hidden={hidden} onHideLabel={hideLabel} enlargeK={enlargeK} />
        <div style={{ position: "absolute", top: 14, left: 14, color: "#64748b", fontSize: 13, fontFamily: "system-ui, sans-serif", pointerEvents: "none" }}>
          Drag to rotate · scroll to zoom · right-drag to pan
        </div>

        {sourceImage && (
          <div style={{ position: "absolute", bottom: 14, right: 14, width: 260, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 10, padding: 8, boxShadow: "0 6px 24px rgba(0,0,0,0.5)", fontFamily: "system-ui, sans-serif" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: "#94a3b8" }}>Original question</span>
              <button onClick={() => setSourceImage(null)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
            </div>
            <img src={sourceImage} alt="original question" style={{ width: "100%", borderRadius: 6, display: "block" }} />
          </div>
        )}
      </div>

      {importing && (
        <ImportDropzone
          onClose={() => setImporting(false)}
          onApply={(id, vals, previewUrl) => {
            setShapeId(id)
            setValues({ ...defaultsFor(id), ...vals })
            setSourceImage(previewUrl)
            setImporting(false)
          }}
        />
      )}
    </div>
  )
}
