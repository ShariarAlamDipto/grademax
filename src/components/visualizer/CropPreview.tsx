"use client"

// Interactive crop: drag a box over the source image to isolate the diagram.
// Reports the selection as normalised (0–1) coords so it maps to any image size.

import { useRef, useState } from "react"

export interface CropRect {
  x: number
  y: number
  w: number
  h: number
}

export default function CropPreview({ src, onCrop }: { src: string; onCrop: (r: CropRect | null) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const [rect, setRect] = useState<CropRect | null>(null)
  const [start, setStart] = useState<{ x: number; y: number } | null>(null)

  const rel = (e: React.MouseEvent) => {
    const b = ref.current!.getBoundingClientRect()
    return { x: Math.min(1, Math.max(0, (e.clientX - b.left) / b.width)), y: Math.min(1, Math.max(0, (e.clientY - b.top) / b.height)) }
  }

  const down = (e: React.MouseEvent) => {
    const p = rel(e)
    setStart(p)
    setRect({ x: p.x, y: p.y, w: 0, h: 0 })
    onCrop(null)
  }
  const move = (e: React.MouseEvent) => {
    if (!start) return
    const p = rel(e)
    setRect({ x: Math.min(start.x, p.x), y: Math.min(start.y, p.y), w: Math.abs(p.x - start.x), h: Math.abs(p.y - start.y) })
  }
  const up = () => {
    if (rect && rect.w > 0.03 && rect.h > 0.03) onCrop(rect)
    setStart(null)
  }

  return (
    <div ref={ref} onMouseDown={down} onMouseMove={move} onMouseUp={up} onMouseLeave={up} style={{ position: "relative", cursor: "crosshair", userSelect: "none" }}>
      <img src={src} alt="source" draggable={false} style={{ width: "100%", borderRadius: 8, border: "1px solid #1e293b", display: "block" }} />
      {rect && rect.w > 0 && (
        <div style={{ position: "absolute", left: `${rect.x * 100}%`, top: `${rect.y * 100}%`, width: `${rect.w * 100}%`, height: `${rect.h * 100}%`, border: "2px solid #a78bfa", background: "rgba(167,139,250,0.15)", pointerEvents: "none" }} />
      )}
    </div>
  )
}

/** Crop an image (data URL) to a normalised rect → new data URL. */
export async function cropToDataUrl(url: string, rect: CropRect): Promise<string> {
  const img = await new Promise<HTMLImageElement>((res, rej) => {
    const im = new Image()
    im.onload = () => res(im)
    im.onerror = rej
    im.src = url
  })
  const sx = rect.x * img.naturalWidth
  const sy = rect.y * img.naturalHeight
  const sw = Math.max(1, rect.w * img.naturalWidth)
  const sh = Math.max(1, rect.h * img.naturalHeight)
  const c = document.createElement("canvas")
  c.width = Math.round(sw)
  c.height = Math.round(sh)
  const ctx = c.getContext("2d")!
  ctx.fillStyle = "#fff"
  ctx.fillRect(0, 0, c.width, c.height)
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height)
  return c.toDataURL("image/png")
}
