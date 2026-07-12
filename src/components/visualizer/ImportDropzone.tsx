"use client"

// Drag/drop a screenshot, photo or PDF → read it ($0, in-browser) → show an
// EDITABLE confirm card. Nothing reaches the diagram until the teacher taps
// "Use this diagram", so an OCR misread is never shown to the class.

import { useCallback, useRef, useState } from "react"
import { readImport, type ImportSource } from "./core/importSource"
import { extractFromText } from "./core/extract"
import { shapes, shapeList, defaultsFor } from "./core/registry"
import type { ShapeId } from "./core/types"
import CropPreview, { cropToDataUrl, type CropRect } from "./CropPreview"

interface Props {
  onApply: (shapeId: ShapeId, values: Record<string, number>, previewUrl: string) => void
  onClose: () => void
}

type Phase = "drop" | "reading" | "review" | "error"

const overlay: React.CSSProperties = {
  position: "fixed", inset: 0, background: "rgba(2,6,23,0.8)", display: "grid", placeItems: "center", zIndex: 50,
  fontFamily: "system-ui, sans-serif",
}
const card: React.CSSProperties = {
  width: "min(720px, 92vw)", maxHeight: "90vh", overflowY: "auto", background: "#0f172a", color: "#e2e8f0",
  borderRadius: 14, padding: 24, border: "1px solid #1e293b",
}
const input: React.CSSProperties = {
  width: 90, padding: "6px 8px", fontSize: 15, borderRadius: 6, border: "1px solid #334155", background: "#1e293b", color: "#fff",
}

const confColor = { high: "#22c55e", medium: "#eab308", low: "#f97316" }

export default function ImportDropzone({ onApply, onClose }: Props) {
  const [phase, setPhase] = useState<Phase>("drop")
  const [progress, setProgress] = useState("")
  const [pct, setPct] = useState(0)
  const [preview, setPreview] = useState("")
  const [rawText, setRawText] = useState("")
  const [source, setSource] = useState<ImportSource>("ocr")
  const [shapeId, setShapeId] = useState<ShapeId>("cuboid")
  const [values, setValues] = useState<Record<string, number>>({})
  const [confidence, setConfidence] = useState<"high" | "medium" | "low">("low")
  const [note, setNote] = useState("")
  const [errMsg, setErrMsg] = useState("")
  const [visionBusy, setVisionBusy] = useState(false)
  const [visionNote, setVisionNote] = useState("")
  const [cropRect, setCropRect] = useState<CropRect | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const recogniseShape = useCallback(async () => {
    setVisionBusy(true)
    setVisionNote(cropRect ? "Looking at the cropped diagram…" : "Looking at the picture…")
    const { classifyShapeLocal } = await import("./core/shapeModel")
    const imgUrl = cropRect ? await cropToDataUrl(preview, cropRect) : preview
    const res = await classifyShapeLocal(imgUrl)
    if (res && res.score > 0.45) {
      setShapeId(res.shape)
      setVisionNote(`Looks like a ${shapes[res.shape].name.toLowerCase()} (${Math.round(res.score * 100)}%).`)
    } else if (res) {
      setShapeId(res.shape)
      setVisionNote(`Best guess: ${shapes[res.shape].name.toLowerCase()} (${Math.round(res.score * 100)}%) — low confidence, please check.`)
    } else {
      setVisionNote("Couldn't read the shape from the diagram — pick it manually.")
    }
    setVisionBusy(false)
  }, [preview, cropRect])

  const handleFile = useCallback(async (file: File) => {
    setPhase("reading")
    setProgress("Reading…")
    setPct(0)
    try {
      const out = await readImport(file, (stage, p) => { setProgress(stage); if (p != null) setPct(p) })
      const res = extractFromText(out.text)
      setPreview(out.previewUrl)
      setRawText(out.text)
      setSource(out.source)
      setShapeId(res.shapeId)
      setValues(res.values)
      setConfidence(out.ocrFailed ? "low" : res.confidence)
      setNote(
        out.ocrFailed
          ? "Couldn't read the text automatically on this device — pick the shape and type the values from the question. Your diagram is shown on the left."
          : res.note,
      )
      setPhase("review")
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "Could not read that file.")
      setPhase("error")
    }
  }, [])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f) handleFile(f)
  }

  const changeShape = (id: ShapeId) => {
    setShapeId(id)
    setValues((prev) => ({ ...defaultsFor(id), ...Object.fromEntries(shapes[id].params.filter((p) => prev[p.key] != null).map((p) => [p.key, prev[p.key]])) }))
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={card} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Import question</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 22, cursor: "pointer" }}>×</button>
        </div>

        {phase === "drop" && (
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            style={{ border: "2px dashed #334155", borderRadius: 12, padding: "48px 20px", textAlign: "center", cursor: "pointer", background: "#0b1220" }}
          >
            <div style={{ fontSize: 40, marginBottom: 10 }}>🖼️</div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>Drop a screenshot, photo or PDF here</div>
            <div style={{ color: "#94a3b8", fontSize: 13, marginTop: 6 }}>…or click to choose a file. Everything runs on this device — nothing is uploaded.</div>
            <input ref={fileRef} type="file" accept="image/*,application/pdf" hidden onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </div>
        )}

        {phase === "reading" && (
          <div style={{ padding: "40px 10px", textAlign: "center" }}>
            <div style={{ fontSize: 15, marginBottom: 12 }}>{progress}</div>
            <div style={{ height: 8, background: "#1e293b", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${Math.round(pct * 100)}%`, background: "#2563eb", transition: "width .2s" }} />
            </div>
            <div style={{ color: "#64748b", fontSize: 12, marginTop: 10 }}>First OCR run downloads the free language data (~a few seconds).</div>
          </div>
        )}

        {phase === "error" && (
          <div style={{ padding: 20 }}>
            <p style={{ color: "#f87171" }}>{errMsg}</p>
            <button onClick={() => setPhase("drop")} style={btn}>Try another file</button>
          </div>
        )}

        {phase === "review" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
            <div>
              {preview && <CropPreview src={preview} onCrop={setCropRect} />}
              <div style={{ fontSize: 12, color: cropRect ? "#a78bfa" : "#64748b", marginTop: 6 }}>
                {cropRect ? "✓ Diagram selected — now click Recognise." : "Tip: drag a box around the diagram, then Recognise."}
              </div>
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                Read via {source === "pdf-text" ? "PDF text layer (accurate)" : "OCR"}.
              </div>
              <details style={{ marginTop: 8, fontSize: 12, color: "#94a3b8" }}>
                <summary style={{ cursor: "pointer" }}>Show extracted text</summary>
                <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{rawText.slice(0, 600) || "(none)"}</pre>
              </details>
            </div>

            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: confColor[confidence], marginBottom: 6 }}>
                {confidence.toUpperCase()} confidence
              </div>
              <p style={{ fontSize: 13, color: "#cbd5e1", marginTop: 0 }}>{note}</p>

              <label style={{ display: "block", marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: "#94a3b8" }}>Shape</span>
                <select value={shapeId} onChange={(e) => changeShape(e.target.value as ShapeId)} style={{ ...input, width: "100%", marginTop: 4 }}>
                  {shapeList.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </label>
              <button onClick={recogniseShape} disabled={visionBusy} style={{ ...btn, background: "#7c3aed", padding: "7px 12px", fontSize: 13, marginBottom: 8, opacity: visionBusy ? 0.6 : 1 }}>
                {visionBusy ? "Looking…" : "🔍 Recognise shape from the picture"}
              </button>
              {visionNote && <p style={{ fontSize: 12.5, color: "#c4b5fd", margin: "0 0 10px" }}>{visionNote}</p>}

              {shapes[shapeId].params.map((spec) => (
                <label key={spec.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 14 }}>{spec.label} (<i>{spec.symbol}</i>)</span>
                  <span>
                    <input
                      type="number" min={spec.min} step={spec.step}
                      value={values[spec.key] ?? spec.default}
                      onChange={(e) => setValues((v) => ({ ...v, [spec.key]: Math.max(spec.min, Number(e.target.value) || spec.min) }))}
                      style={input}
                    /> <span style={{ fontSize: 12, color: "#94a3b8" }}>{spec.unit}</span>
                  </span>
                </label>
              ))}

              <button onClick={() => onApply(shapeId, values, preview)} style={{ ...btn, background: "#16a34a", marginTop: 12, width: "100%" }}>
                ✓ Use this diagram
              </button>
              <button onClick={() => setPhase("drop")} style={{ ...btn, background: "#334155", marginTop: 8, width: "100%" }}>
                Import a different file
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const btn: React.CSSProperties = {
  padding: "10px 14px", fontSize: 15, fontWeight: 700, borderRadius: 8, border: "none", color: "#fff", cursor: "pointer", background: "#2563eb",
}
