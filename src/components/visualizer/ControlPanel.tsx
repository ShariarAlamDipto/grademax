"use client"

// Control panel — the PRIMARY input and confirm gate. Shape picker + dynamic
// dimension fields + working. Import only pre-fills these same fields.

import type { ShapeId, ShapeModel } from "./core/types"
import { shapes, shapeList } from "./core/registry"
import type { SceneToggles } from "./Scene"

interface Props {
  shapeId: ShapeId
  onShape: (id: ShapeId) => void
  values: Record<string, number>
  onValue: (key: string, n: number) => void
  toggles: SceneToggles
  onToggle: (key: keyof SceneToggles) => void
  showWorking: boolean
  onShowWorking: () => void
  model: ShapeModel
  onImport: () => void
  hidden: Set<string>
  onRestoreLabel: (key: string) => void
  onRestoreAll: () => void
  enlargeK: number
  onEnlargeK: (k: number) => void
}

const wrap: React.CSSProperties = {
  width: 330,
  flexShrink: 0,
  padding: 20,
  background: "#0f172a",
  color: "#e2e8f0",
  borderRight: "1px solid #1e293b",
  overflowY: "auto",
  fontFamily: "system-ui, sans-serif",
}

const field: React.CSSProperties = {
  flex: 1,
  padding: "8px 10px",
  fontSize: 16,
  borderRadius: 6,
  border: "1px solid #334155",
  background: "#1e293b",
  color: "#fff",
}

export default function ControlPanel(p: Props) {
  const template = shapes[p.shapeId]
  const toggleDefs: [keyof SceneToggles, string][] = [
    ["showValues", "Show value labels"],
    ["showVertices", "Show vertex labels"],
    ["showConstruction", "Show construction"],
  ]
  if (p.model.net) toggleDefs.push(["showNet", "Show net (unfold)"])
  return (
    <div style={wrap}>
      <button
        onClick={p.onImport}
        style={{ width: "100%", padding: "11px", marginBottom: 18, fontSize: 15, fontWeight: 700, borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer" }}
      >
        ⬆ Import from photo / PDF
      </button>

      <label style={{ display: "block", marginBottom: 16 }}>
        <span style={{ fontSize: 13, color: "#94a3b8", fontWeight: 600 }}>Shape</span>
        <select value={p.shapeId} onChange={(e) => p.onShape(e.target.value as ShapeId)} style={{ ...field, marginTop: 4, width: "100%" }}>
          {shapeList.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </label>

      {template.params.map((spec) => (
        <label key={spec.key} style={{ display: "block", marginBottom: 14 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{spec.label}{spec.symbol && <> (<i>{spec.symbol}</i>)</>}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            {spec.choices ? (
              <select
                value={p.values[spec.key] ?? spec.default}
                onChange={(e) => p.onValue(spec.key, Number(e.target.value))}
                style={{ ...field, width: "100%" }}
              >
                {spec.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            ) : (
              <>
                <input
                  type="number"
                  min={spec.min}
                  step={spec.step}
                  value={p.values[spec.key] ?? spec.default}
                  onChange={(e) => {
                    const n = Number(e.target.value)
                    p.onValue(spec.key, Number.isFinite(n) ? Math.max(spec.min, n) : spec.min)
                  }}
                  style={field}
                />
                <span style={{ fontSize: 13, color: "#94a3b8" }}>{spec.unit}</span>
              </>
            )}
          </div>
        </label>
      ))}

      <div style={{ marginTop: 18, borderTop: "1px solid #1e293b", paddingTop: 16 }}>
        {toggleDefs.map(([key, txt]) => (
          <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, fontSize: 14, cursor: "pointer" }}>
            <input type="checkbox" checked={p.toggles[key]} onChange={() => p.onToggle(key)} style={{ width: 16, height: 16 }} />
            {txt}
          </label>
        ))}
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, cursor: "pointer" }}>
          <input type="checkbox" checked={p.showWorking} onChange={p.onShowWorking} style={{ width: 16, height: 16 }} />
          Show working
        </label>
      </div>

      {p.model.metrics && (
        <div style={{ marginTop: 16, borderTop: "1px solid #1e293b", paddingTop: 14 }}>
          <label style={{ display: "block" }}>
            <span style={{ fontSize: 13, color: "#94a3b8", fontWeight: 600 }}>Similar solids — scale factor k</span>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
              <input type="number" min={1} step={0.5} value={p.enlargeK} onChange={(e) => p.onEnlargeK(Math.max(1, Number(e.target.value) || 1))} style={field} />
              <span style={{ fontSize: 12, color: "#64748b" }}>1 = off</span>
            </div>
          </label>
          {p.enlargeK > 1 && (
            <div style={{ marginTop: 10, padding: 12, background: "#1e293b", borderRadius: 8, fontSize: 13.5, lineHeight: 1.7 }}>
              <div>Lengths × k = <b>×{+p.enlargeK.toFixed(2)}</b></div>
              <div style={{ color: "#22d3ee" }}>Areas × k² = <b>×{+(p.enlargeK ** 2).toFixed(2)}</b></div>
              <div style={{ color: "#a78bfa" }}>Volumes × k³ = <b>×{+(p.enlargeK ** 3).toFixed(2)}</b></div>
              <div style={{ marginTop: 6, color: "#22d3ee" }}>Surface area: {p.model.metrics.surfaceArea.toFixed(1)} → <b>{(p.model.metrics.surfaceArea * p.enlargeK ** 2).toFixed(1)} cm²</b></div>
              <div style={{ color: "#a78bfa" }}>Volume: {p.model.metrics.volume.toFixed(1)} → <b>{(p.model.metrics.volume * p.enlargeK ** 3).toFixed(1)} cm³</b></div>
            </div>
          )}
        </div>
      )}

      {p.hidden.size > 0 && (
        <div style={{ marginTop: 16, borderTop: "1px solid #1e293b", paddingTop: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "#94a3b8", fontWeight: 600 }}>Hidden labels (click to restore)</span>
            <button onClick={p.onRestoreAll} style={{ fontSize: 12, color: "#93c5fd", background: "none", border: "none", cursor: "pointer" }}>restore all</button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {[...p.hidden].map((key) => (
              <button
                key={key}
                onClick={() => p.onRestoreLabel(key)}
                style={{ fontSize: 13, padding: "3px 9px", borderRadius: 999, border: "1px solid #334155", background: "#1e293b", color: "#e2e8f0", cursor: "pointer" }}
              >
                {key} <span style={{ color: "#64748b" }}>＋</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {p.showWorking && (
        <div style={{ marginTop: 18, padding: 14, background: "#1e293b", borderRadius: 8, fontSize: 13.5, lineHeight: 1.65 }}>
          {p.model.working.map((step, i) => (
            <div key={i} style={{ marginBottom: 10 }}>
              <div style={{ color: step.color ?? "#cbd5e1", fontWeight: 600 }}>{step.title}</div>
              <div>{step.detail}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
