"use client"

import Link from "next/link"
import { useCallback, useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react"
import Image from "next/image"
import { wheelSlots, wrapIndex } from "@/lib/store/bookWheel"

/**
 * The shop's book wheel: every book in the catalogue on one looping fan.
 *
 * It never moves on its own. It turns only when the visitor scrolls the mouse
 * wheel (or two-finger swipes a trackpad) while the pointer is on the books,
 * drags or swipes them, or uses the arrow buttons / arrow keys.
 */

export interface WheelBook {
  slug: string
  title: string
  coverUrl: string
  priceLabel: string
}

interface BookWheelProps {
  books: WheelBook[]
}

/** Books drawn either side of the centre one. */
const REACH = 3
/** Wheel / trackpad delta (px) that turns the wheel by one book. */
const WHEEL_PX_PER_BOOK = 160
/** After this long without input the wheel settles on the nearest book. */
const SETTLE_MS = 170
/** A press that moves less than this is a click on the book, not a drag. */
const CLICK_SLOP_PX = 6

export function BookWheel({ books }: BookWheelProps) {
  const [position, setPosition] = useState(0)
  const [dragging, setDragging] = useState(false)
  const trackRef = useRef<HTMLDivElement>(null)
  const settleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const drag = useRef<{ startX: number; startPosition: number; moved: number } | null>(null)
  // The wheel listens to scrolling only while "armed": after the visitor has
  // really moved the pointer onto the books. Scrolling the page slides the
  // books under a pointer that is standing still, and that must not hijack the
  // scroll, so any page scroll disarms it until the pointer moves again.
  const armed = useRef(false)
  const lastPointer = useRef<{ x: number; y: number } | null>(null)

  const count = books.length

  const settleSoon = useCallback(() => {
    if (settleTimer.current) clearTimeout(settleTimer.current)
    settleTimer.current = setTimeout(() => setPosition(p => Math.round(p)), SETTLE_MS)
  }, [])

  useEffect(() => () => { if (settleTimer.current) clearTimeout(settleTimer.current) }, [])

  // The wheel listener must be non-passive to stop the page scrolling while the
  // pointer is on the books, which React's onWheel cannot guarantee.
  useEffect(() => {
    const track = trackRef.current
    if (!track || count < 2) return
    const onWheel = (event: WheelEvent) => {
      if (!armed.current) return
      const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY
      if (delta === 0) return
      event.preventDefault()
      setPosition(p => p + delta / WHEEL_PX_PER_BOOK)
      settleSoon()
    }
    const disarm = () => { armed.current = false }
    track.addEventListener("wheel", onWheel, { passive: false })
    window.addEventListener("scroll", disarm, { passive: true })
    return () => {
      track.removeEventListener("wheel", onWheel)
      window.removeEventListener("scroll", disarm)
    }
  }, [count, settleSoon])

  /** Width of one step between neighbouring books, in px. */
  const stepPx = (): number => {
    const track = trackRef.current
    if (!track) return 180
    return parseFloat(getComputedStyle(track).getPropertyValue("--bw-step")) || 180
  }

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (count < 2 || (event.pointerType === "mouse" && event.button !== 0)) return
    drag.current = { startX: event.clientX, startPosition: position, moved: 0 }
  }

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    // Browsers send a synthetic move (same coordinates) when content scrolls
    // under the pointer; only a move to new coordinates arms the wheel.
    const last = lastPointer.current
    if (!last || last.x !== event.clientX || last.y !== event.clientY) {
      if (last) armed.current = true
      lastPointer.current = { x: event.clientX, y: event.clientY }
    }
    const state = drag.current
    if (!state) return
    const dx = event.clientX - state.startX
    state.moved = Math.max(state.moved, Math.abs(dx))
    if (state.moved < CLICK_SLOP_PX) return
    if (!dragging) {
      setDragging(true)
      event.currentTarget.setPointerCapture(event.pointerId)
    }
    setPosition(state.startPosition - dx / stepPx())
  }

  const endDrag = () => {
    if (!drag.current) return
    // Keep `moved` readable for the click that follows a pointer-up.
    const moved = drag.current.moved
    drag.current = moved >= CLICK_SLOP_PX ? { startX: 0, startPosition: 0, moved } : null
    setDragging(false)
    setPosition(p => Math.round(p))
    if (moved >= CLICK_SLOP_PX) setTimeout(() => { drag.current = null }, 0)
  }

  const turn = (by: number) => setPosition(p => Math.round(p) + by)

  if (count === 0) return null

  const centre = Math.round(position)
  const current = books[wrapIndex(centre, count)]
  const slots = count === 1 ? [{ key: 0, index: 0, offset: 0 }] : wheelSlots(position, count, REACH)

  return (
    <div className="bw" role="group" aria-roledescription="carousel" aria-label="All GradeMax books">
      <div
        ref={trackRef}
        className="bw-track"
        data-dragging={dragging || undefined}
        tabIndex={0}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={() => { armed.current = false; lastPointer.current = null }}
        onKeyDown={event => {
          if (event.key === "ArrowLeft") { event.preventDefault(); turn(-1) }
          if (event.key === "ArrowRight") { event.preventDefault(); turn(1) }
        }}
      >
        {slots.map(slot => {
          const book = books[slot.index]
          const distance = Math.abs(slot.offset)
          const style = {
            "--d": slot.offset.toFixed(3),
            "--a": distance.toFixed(3),
            zIndex: 100 - Math.round(distance * 10),
            opacity: distance > REACH - 0.4 ? 0 : 1,
          } as CSSProperties
          const isCentre = slot.key === centre
          return (
            <Link
              key={slot.key}
              href={`/store/${book.slug}`}
              className="bw-book"
              style={style}
              draggable={false}
              tabIndex={isCentre ? 0 : -1}
              aria-hidden={isCentre ? undefined : true}
              aria-label={book.title}
              onClick={event => {
                // A drag must not open the book it ended on; a click on a side
                // book brings it to the centre first.
                if (drag.current && drag.current.moved >= CLICK_SLOP_PX) { event.preventDefault(); return }
                if (!isCentre) { event.preventDefault(); setPosition(slot.key) }
              }}
            >
              <Image src={book.coverUrl} alt="" fill sizes="(max-width: 640px) 40vw, 220px" style={{ objectFit: "cover" }} priority={distance < 2.5} />
            </Link>
          )
        })}
      </div>

      <div className="bw-caption">
        <button type="button" className="bw-arrow" onClick={() => turn(-1)} aria-label="Previous book" disabled={count < 2}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><path strokeLinecap="round" strokeLinejoin="round" d="M15 6l-6 6 6 6" /></svg>
        </button>
        <div className="bw-current" aria-live="polite">
          <Link href={`/store/${current.slug}`} className="bw-title">{current.title}</Link>
          <span className="bw-meta">{current.priceLabel} · {wrapIndex(centre, count) + 1} of {count}</span>
        </div>
        <button type="button" className="bw-arrow" onClick={() => turn(1)} aria-label="Next book" disabled={count < 2}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><path strokeLinecap="round" strokeLinejoin="round" d="M9 6l6 6-6 6" /></svg>
        </button>
      </div>
      <p className="bw-hint">Scroll or swipe on the books to turn them</p>
    </div>
  )
}
