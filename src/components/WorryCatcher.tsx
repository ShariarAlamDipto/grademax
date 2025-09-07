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

type Crumb = {
  x: number
  y: number
  tx: number // target offset inside net (relative)
  ty: number
}

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
  const doneRef = useRef(false)

  useEffect(() => {
    const canvas = canvasRef.current
    const wrapper = wrapperRef.current
    if (!canvas || !wrapper) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = Math.max(1, window.devicePixelRatio || 1)
    let w = wrapper.clientWidth
    let h = Math.max(520, Math.floor(wrapper.clientWidth * 0.55))

    const resizeCanvas = () => {
      w = wrapper.clientWidth
      h = Math.max(520, Math.floor(wrapper.clientWidth * 0.55))
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.scale(dpr, dpr)
    }
    resizeCanvas()

    const rand = (min: number, max: number) => Math.random() * (max - min) + min
    const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))

    // Measure-based radius (bigger for longer words)
    const font = "600 12px system-ui, -apple-system, Segoe UI, Roboto"
    ctx.font = font
    const radiusFor = (t: string) => {
      const width = ctx.measureText(t).width
      return clamp(width * 0.6 + 18, 26, 64)
    }

    // Create bubbles
    const bubbles: Bubble[] = WORRIES.map((text, i) => ({
      id: i,
      text,
      x: rand(60, w - 60),
      y: rand(60, h - 120),
      vx: rand(-0.35, 0.35),
      vy: rand(-0.30, 0.30),
      r: radiusFor(text),
      captured: false,
    }))

    const crumbs: Crumb[] = []
    const mouse = { x: w / 2, y: h / 2 }
    const netRadius = 48

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      mouse.x = e.clientX - rect.left
      mouse.y = e.clientY - rect.top
    }
    canvas.addEventListener("mousemove", onMove)
    window.addEventListener("resize", resizeCanvas)

    // --- Physics helpers ---
    function resolveBubbleCollisions() {
      // naive O(n^2) – fine for small n
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
            // Separate
            const overlap = (minDist - dist) * 0.5
            const nx = dx / dist
            const ny = dy / dist
            bi.x += nx * overlap
            bi.y += ny * overlap
            bj.x -= nx * overlap
            bj.y -= ny * overlap

            // Elastic bounce (equal mass)
            const rvx = bi.vx - bj.vx
            const rvy = bi.vy - bj.vy
            const velAlongNormal = rvx * nx + rvy * ny
            if (velAlongNormal < 0) {
              const e = 0.95 // restitution
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

    let anim = 0
    const tick = () => {
      ctx.clearRect(0, 0, w, h)

      // Subtle grid background
      ctx.globalAlpha = 0.05
      for (let gx = 0; gx < w; gx += 32) {
        ctx.beginPath()
        ctx.moveTo(gx, 0)
        ctx.lineTo(gx, h)
        ctx.strokeStyle = "#fff"
        ctx.stroke()
      }
      for (let gy = 0; gy < h; gy += 32) {
        ctx.beginPath()
        ctx.moveTo(0, gy)
        ctx.lineTo(w, gy)
        ctx.strokeStyle = "#fff"
        ctx.stroke()
      }
      ctx.globalAlpha = 1

      // Update bubble positions & wall bounces
      let allCaptured = true
      for (const b of bubbles) {
        if (b.captured) continue
        allCaptured = false

        b.x += b.vx
        b.y += b.vy
        // walls
        if (b.x < b.r) { b.x = b.r; b.vx *= -1 }
        if (b.x > w - b.r) { b.x = w - b.r; b.vx *= -1 }
        if (b.y < b.r) { b.y = b.r; b.vy *= -1 }
        if (b.y > h - b.r) { b.y = h - b.r; b.vy *= -1 }
      }

      // Resolve bubble-bubble collisions
      resolveBubbleCollisions()

      // Catching with net
      for (const b of bubbles) {
        if (b.captured) continue
        const dx = b.x - mouse.x
        const dy = b.y - mouse.y
        const dist = Math.hypot(dx, dy)
        if (dist <= b.r + netRadius * 0.65) {
          b.captured = true
          // spawn paper crumbs that fly into the net & stay inside
          for (let i = 0; i < 10; i++) {
            const angle = Math.random() * Math.PI * 2
            const r = rand(6, netRadius - 6)
            // target offsets inside net circle
            const tx = Math.cos(angle) * r
            const ty = Math.sin(angle) * r
            crumbs.push({ x: b.x, y: b.y, tx, ty })
          }
        }
      }

      // Draw bubbles (glass style)
      for (const b of bubbles) {
        if (b.captured) continue

        // soft drop shadow
        ctx.save()
        ctx.shadowColor = "rgba(0,0,0,0.35)"
        ctx.shadowBlur = 18
        ctx.shadowOffsetY = 6

        // glassy fill
        const grd = ctx.createRadialGradient(
          b.x - b.r * 0.3, b.y - b.r * 0.3, b.r * 0.2,
          b.x, b.y, b.r
        )
        grd.addColorStop(0, "rgba(255,255,255,0.55)")
        grd.addColorStop(0.6, "rgba(255,255,255,0.18)")
        grd.addColorStop(1, "rgba(255,255,255,0.08)")
        ctx.fillStyle = grd
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()

        // rim
        ctx.strokeStyle = "rgba(255,255,255,0.35)"
        ctx.lineWidth = 1.2
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r - 0.6, 0, Math.PI * 2)
        ctx.stroke()

        // specular highlight
        ctx.beginPath()
        ctx.arc(b.x - b.r * 0.35, b.y - b.r * 0.35, b.r * 0.25, Math.PI * 0.1, Math.PI * 1.1)
        ctx.strokeStyle = "rgba(255,255,255,0.45)"
        ctx.lineWidth = 1
        ctx.stroke()

        // label
        ctx.fillStyle = "rgba(10,10,10,0.9)"
        ctx.font = font
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(b.text, b.x, b.y)
      }

      // Draw crumbs (fly into net, then follow net center + target offset)
      ctx.fillStyle = "#ffffff"
      for (const c of crumbs) {
        c.x += (mouse.x + c.tx - c.x) * 0.18
        c.y += (mouse.y + c.ty - c.y) * 0.18
      }

      // ---- Draw NET (rim + clipped mesh + crumbs inside only) ----
      drawNet(ctx, mouse.x, mouse.y, netRadius, crumbs)

      if (allCaptured && !doneRef.current) {
        doneRef.current = true
        setDone(true)
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
    <section className="mx-auto max-w-6xl px-6 pb-24 text-center mt-20">
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
              <p className="text-lg md:text-xl font-semibold">GradeMax will solve it all ✨</p>
            </div>
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-gray-400">Move your mouse and catch the worries with the net.</p>
    </section>
  )
}

/* ------------ helpers ------------- */
function drawNet(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  crumbs: Crumb[],
) {
  ctx.save()
  ctx.translate(x, y)

  // Rim gradient
  const rim = ctx.createRadialGradient(-r * 0.2, -r * 0.2, r * 0.3, 0, 0, r)
  rim.addColorStop(0, "rgba(255,255,255,0.95)")
  rim.addColorStop(0.5, "rgba(255,255,255,0.7)")
  rim.addColorStop(1, "rgba(255,255,255,0.35)")

  // Outer rim
  ctx.beginPath()
  ctx.arc(0, 0, r, 0, Math.PI * 2)
  ctx.lineWidth = 3
  ctx.strokeStyle = rim
  ctx.stroke()

  // clip area (everything inside the hoop)
  ctx.save()
  ctx.beginPath()
  ctx.arc(0, 0, r - 1.5, 0, Math.PI * 2)
  ctx.clip()

  // Mesh lines (clipped)
  ctx.globalAlpha = 0.65
  ctx.lineWidth = 1
  ctx.strokeStyle = "rgba(255,255,255,0.85)"
  const step = 8
  for (let a = -r; a <= r; a += step) {
    ctx.beginPath()
    ctx.moveTo(-r, a)
    ctx.lineTo(r, a)
    ctx.stroke()
  }
  for (let a = -r; a <= r; a += step) {
    ctx.beginPath()
    ctx.moveTo(a, -r)
    ctx.lineTo(a, r)
    ctx.stroke()
  }
  ctx.globalAlpha = 1

  // Draw crumbs INSIDE the clipped circle only
  ctx.fillStyle = "#ffffff"
  for (const c of crumbs) {
    // Only draw if within circle – keeps crumbs "retained" in round shape
    const dx = c.x - x
    const dy = c.y - y
    if (dx * dx + dy * dy <= (r - 3) * (r - 3)) {
      ctx.fillRect(dx - 1.5, dy - 1.5, 3, 3)
    }
  }

  ctx.restore()

  // Handle (angled)
  ctx.beginPath()
  ctx.moveTo(r * 0.15, r)
  ctx.lineTo(r * 0.15, r + 42)
  ctx.lineWidth = 4
  ctx.strokeStyle = "rgba(255,255,255,0.85)"
  ctx.stroke()

  ctx.restore()
}
