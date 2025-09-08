"use client"

import { useEffect, useRef, useState } from "react"

type Bubble = {
  id: number
  text: string
  x: number
  y: number
  vx: number
  vy: number
  r: number
  captured: boolean
}

type Crumb = { x: number; y: number; tx: number; ty: number }

const WORRIES = [
  "Procrastination",
  "Deadlines",
  "Stress",
  "Confusion",
  "Revision Overload",
  "Time Management",
  "Exam Fear",
  "Motivation",
  "Doubts",
  "Distractions",
  "Anxiety",
  "Burnout",
]

export default function WorryCatcher() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [done, setDone] = useState(false)
  const [elapsed, setElapsed] = useState<number | null>(null)
  const doneRef = useRef(false)
  const startTimeRef = useRef<number | null>(null)

  useEffect(() => {
    // Start timer on mount
    startTimeRef.current = performance.now()
    const canvas = canvasRef.current
    const wrapper = wrapperRef.current
    if (!canvas || !wrapper) return

    const ctxMaybe = canvas.getContext("2d")
    if (!ctxMaybe) return
    const c = ctxMaybe // <- non-null ctx captured for all inner functions

    const dpr = Math.max(1, window.devicePixelRatio || 1)
    let w = wrapper.clientWidth
    let h = Math.max(560, Math.floor(wrapper.clientWidth * 0.55))

    const resizeCanvas = () => {
      w = wrapper.clientWidth
      h = Math.max(560, Math.floor(wrapper.clientWidth * 0.55))
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      c.setTransform(1, 0, 0, 1, 0, 0)
      c.scale(dpr, dpr)
    }
    resizeCanvas()

    const rand = (min: number, max: number) => Math.random() * (max - min) + min
    const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))

    // radius by text length
    const labelFont = "600 12px system-ui, -apple-system, Segoe UI, Roboto"
    c.font = labelFont
    const radiusFor = (t: string) => {
      const width = c.measureText(t).width
      return clamp(width * 0.6 + 18, 26, 70)
    }

    // bubbles
    const bubbles: Bubble[] = WORRIES.map((text, i) => ({
      id: i,
      text,
      x: rand(70, w - 70),
      y: rand(70, h - 140),
      vx: rand(-0.65, 0.65),
      vy: rand(-0.55, 0.55),
      r: radiusFor(text),
      captured: false,
    }))

    const crumbs: Crumb[] = []
    const mouse = { x: w / 2, y: h / 2 }
    const netRadius = 48
    const MAX_SPEED = 0.9
    const DRIFT = 0.015
    const FRICTION = 0.999

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      mouse.x = e.clientX - rect.left
      mouse.y = e.clientY - rect.top
    }
    canvas.addEventListener("mousemove", onMove)
    window.addEventListener("resize", resizeCanvas)

    // ----- collisions -----
    function resolveBubbleCollisions() {
      for (let i = 0; i < bubbles.length; i++) {
        const bi = bubbles[i]
        if (bi.captured) continue
        for (let j = i + 1; j < bubbles.length; j++) {
          const bj = bubbles[j]
          if (bj.captured) continue
          const dx = bi.x - bj.x
          const dy = bi.y - bj.y
          const dist = Math.hypot(dx, dy)
          const minDist = bi.r + bj.r
          if (dist < minDist && dist > 0.0001) {
            // separate
            const overlap = (minDist - dist) * 0.5
            const nx = dx / dist
            const ny = dy / dist
            bi.x += nx * overlap
            bi.y += ny * overlap
            bj.x -= nx * overlap
            bj.y -= ny * overlap
            // elastic bounce (equal mass)
            const rvx = bi.vx - bj.vx
            const rvy = bi.vy - bj.vy
            const velAlongNormal = rvx * nx + rvy * ny
            if (velAlongNormal < 0) {
              const e = 0.96
              const jImp = -(1 + e) * velAlongNormal / 2
              bi.vx += jImp * nx
              bi.vy += jImp * ny
              bj.vx -= jImp * nx
              bj.vy -= jImp * ny
            }
          }
        }
      }
    }

    // ----- draw helpers (glassy bubble) -----
    function drawGlassBubble(x: number, y: number, r: number, text: string) {
      // halo / lens glow
      c.save()
      c.globalCompositeOperation = "screen"
      const halo = c.createRadialGradient(x, y, r * 0.2, x, y, r * 1.6)
      halo.addColorStop(0, "rgba(255,255,255,0.07)")
      halo.addColorStop(1, "rgba(255,255,255,0)")
      c.fillStyle = halo
      c.beginPath()
      c.arc(x, y, r * 1.5, 0, Math.PI * 2)
      c.fill()
      c.restore()

      // body + shadow
      c.save()
      c.shadowColor = "rgba(0,0,0,0.35)"
      c.shadowBlur = 22
      c.shadowOffsetY = 7
      const body = c.createRadialGradient(x - r * 0.28, y - r * 0.28, r * 0.2, x, y, r)
      body.addColorStop(0, "rgba(255,255,255,0.60)")
      body.addColorStop(0.55, "rgba(255,255,255,0.18)")
      body.addColorStop(1, "rgba(255,255,255,0.10)")
      c.fillStyle = body
      c.beginPath()
      c.arc(x, y, r, 0, Math.PI * 2)
      c.fill()
      c.restore()

      // rim
      c.strokeStyle = "rgba(255,255,255,0.38)"
      c.lineWidth = 1.2
      c.beginPath()
      c.arc(x, y, r - 0.6, 0, Math.PI * 2)
      c.stroke()

      // inner glow (blurred, clipped)
      c.save()
      c.beginPath()
      c.arc(x, y, r * 0.82, 0, Math.PI * 2)
      c.clip()
  c.filter = "blur(6px)"
      c.globalAlpha = 0.18
      c.fillStyle = "#fff"
      c.beginPath()
      c.arc(x - r * 0.2, y - r * 0.2, r * 0.75, 0, Math.PI * 2)
      c.fill()
  c.filter = "none"
      c.globalAlpha = 1
      c.restore()

      // caustic reflection arcs
      c.save()
      c.lineCap = "round"
      c.strokeStyle = "rgba(255,255,255,0.55)"
      c.lineWidth = 1.2
      c.beginPath()
      c.arc(x - r * 0.28, y - r * 0.32, r * 0.55, Math.PI * 0.1, Math.PI * 0.9)
      c.stroke()
      c.globalAlpha = 0.4
      c.beginPath()
      c.arc(x + r * 0.15, y + r * 0.2, r * 0.4, Math.PI * 1.2, Math.PI * 1.9)
      c.stroke()
      c.restore()

      // label
      c.fillStyle = "rgba(10,10,10,0.92)"
      c.font = labelFont
      c.textAlign = "center"
      c.textBaseline = "middle"
      c.fillText(text, x, y)
    }

    function drawNet(
      ctx: CanvasRenderingContext2D,
      x: number,
      y: number,
      r: number,
      crumbs: Crumb[],
    ) {
      const g = ctx // alias

      g.save()
      g.translate(x, y)

      // rim gradient
      const rim = g.createRadialGradient(-r * 0.2, -r * 0.2, r * 0.3, 0, 0, r)
      rim.addColorStop(0, "rgba(255,255,255,0.95)")
      rim.addColorStop(0.5, "rgba(255,255,255,0.7)")
      rim.addColorStop(1, "rgba(255,255,255,0.35)")

      // outer rim
      g.beginPath()
      g.arc(0, 0, r, 0, Math.PI * 2)
      g.lineWidth = 3
      g.strokeStyle = rim
      g.stroke()

      // clip to circle
      g.save()
      g.beginPath()
      g.arc(0, 0, r - 1.5, 0, Math.PI * 2)
      g.clip()

      // mesh
      g.globalAlpha = 0.65
      g.lineWidth = 1
      g.strokeStyle = "rgba(255,255,255,0.85)"
      const step = 8
      for (let a = -r; a <= r; a += step) {
        g.beginPath()
        g.moveTo(-r, a)
        g.lineTo(r, a)
        g.stroke()
      }
      for (let a = -r; a <= r; a += step) {
        g.beginPath()
        g.moveTo(a, -r)
        g.lineTo(a, r)
        g.stroke()
      }
      g.globalAlpha = 1

      // draw crumbs inside hoop only
      g.fillStyle = "#fff"
      for (const c of crumbs) {
        const dx = c.x - x
        const dy = c.y - y
        if (dx * dx + dy * dy <= (r - 3) * (r - 3)) {
          g.fillRect(dx - 1.5, dy - 1.5, 3, 3)
        }
      }
      g.restore()

      // handle
      g.beginPath()
      g.moveTo(r * 0.15, r)
      g.lineTo(r * 0.15, r + 42)
      g.lineWidth = 4
      g.strokeStyle = "rgba(255,255,255,0.85)"
      g.stroke()

      g.restore()
    }

    // ----- main loop -----
    let anim = 0
    const tick = () => {
      // clear
      c.clearRect(0, 0, w, h)

      // subtle grid
      c.globalAlpha = 0.05
      for (let gx = 0; gx < w; gx += 32) {
        c.beginPath()
        c.moveTo(gx, 0)
        c.lineTo(gx, h)
        c.strokeStyle = "#fff"
        c.stroke()
      }
      for (let gy = 0; gy < h; gy += 32) {
        c.beginPath()
        c.moveTo(0, gy)
        c.lineTo(w, gy)
        c.strokeStyle = "#fff"
        c.stroke()
      }
      c.globalAlpha = 1

      // motion update
      let allCaptured = true
      for (const b of bubbles) {
        if (b.captured) continue
        allCaptured = false

        // drift + friction + clamp
        b.vx = clamp((b.vx + rand(-DRIFT, DRIFT)) * FRICTION, -MAX_SPEED, MAX_SPEED)
        b.vy = clamp((b.vy + rand(-DRIFT, DRIFT)) * FRICTION, -MAX_SPEED, MAX_SPEED)

        b.x += b.vx
        b.y += b.vy
        // walls
        if (b.x < b.r) { b.x = b.r; b.vx *= -1 }
        if (b.x > w - b.r) { b.x = w - b.r; b.vx *= -1 }
        if (b.y < b.r) { b.y = b.r; b.vy *= -1 }
        if (b.y > h - b.r) { b.y = h - b.r; b.vy *= -1 }
      }

      // collisions
      resolveBubbleCollisions()

      // net catching → spawn crumbs
      for (const b of bubbles) {
        if (b.captured) continue
        const dx = b.x - mouse.x
        const dy = b.y - mouse.y
        const dist = Math.hypot(dx, dy)
        if (dist <= b.r + netRadius * 0.65) {
          b.captured = true
          for (let i = 0; i < 10; i++) {
            const angle = Math.random() * Math.PI * 2
            const r = rand(6, netRadius - 6)
            crumbs.push({ x: b.x, y: b.y, tx: Math.cos(angle) * r, ty: Math.sin(angle) * r })
          }
        }
      }

      // draw bubbles
      for (const b of bubbles) {
        if (!b.captured) drawGlassBubble(b.x, b.y, b.r, b.text)
      }

      // crumbs ease into the net
      c.fillStyle = "#fff"
      for (const p of crumbs) {
        p.x += (mouse.x + p.tx - p.x) * 0.18
        p.y += (mouse.y + p.ty - p.y) * 0.18
      }

      // net (hoop + clipped mesh + crumbs inside)
      drawNet(c, mouse.x, mouse.y, netRadius, crumbs)

      if (allCaptured && !doneRef.current) {
        doneRef.current = true
        setDone(true)
        if (startTimeRef.current !== null) {
          setElapsed(performance.now() - startTimeRef.current)
        }
      }

      anim = requestAnimationFrame(tick)
    }

    tick()

    return () => {
      cancelAnimationFrame(anim)
      canvas.removeEventListener("mousemove", onMove)
      window.removeEventListener("resize", resizeCanvas)
    }
  }, [])

  return (
    <section className="mx-auto max-w-6xl px-6 pb-24 text-center">
      <h2 className="text-3xl md:text-4xl font-semibold mb-6">Catch your problems</h2>
      <div
        ref={wrapperRef}
        className="relative w-full h-[560px] rounded-2xl border border-white/10 bg-gradient-to-b from-white/5 to-transparent overflow-hidden cursor-none"
        aria-label="Interactive area: catch your problems"
      >
        <canvas ref={canvasRef} className="w-full h-full" />
        {done && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="rounded-xl bg-black/70 px-5 py-3 text-center">
              {elapsed !== null ? (
                <p className="text-lg md:text-xl font-semibold">
                  You caught your problems in: {(elapsed / 1000).toFixed(3)} seconds
                </p>
              ) : (
                <p className="text-lg md:text-xl font-semibold">GradeMax will solve it all ✨</p>
              )}
            </div>
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-gray-400">Move your mouse and catch the worries with the net.</p>
    </section>
  )
}
