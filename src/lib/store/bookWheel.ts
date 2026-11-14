/** Geometry of the shop's looping book wheel (see components/store/BookWheel.tsx). */

/** Index wrapped into 0..count-1, for any integer (negative included). */
export function wrapIndex(index: number, count: number): number {
  return ((index % count) + count) % count
}

export interface WheelSlot {
  /** Unbounded position on the wheel; stable while the wheel turns, so it is the React key. */
  key: number
  /** Which book sits in the slot. */
  index: number
  /** Distance from the centre in books: negative is left, 0 is centred. */
  offset: number
}

/**
 * The slots to draw for a wheel at `position` (a fractional book index that
 * grows without bound in either direction): the nearest book and `reach`
 * neighbours on each side, looping over `count` books.
 */
export function wheelSlots(position: number, count: number, reach: number): WheelSlot[] {
  if (count <= 0) return []
  const centre = Math.round(position)
  const slots: WheelSlot[] = []
  for (let step = -reach; step <= reach; step++) {
    const key = centre + step
    slots.push({ key, index: wrapIndex(key, count), offset: key - position })
  }
  return slots
}
