/**
 * Browser storage for the cart, and who it belongs to.
 *
 * The cart lives in localStorage, which belongs to the browser, not to the
 * person signed in. Without an owner, a cart filled by one account was shown to
 * the next account that signed in on the same device, and "Buy now" added to
 * it, so a second buyer could place an order containing the first buyer's
 * items. Each stored cart now records the account it was filled under, and
 * `reconcileCartOwner` is called on every auth change to enforce it:
 *
 *   - guest cart, someone signs in   -> they adopt it (checkout requires an
 *                                        account, so this is the normal path)
 *   - account A's cart, B signs in   -> emptied
 *   - account A's cart, signed out   -> emptied
 *
 * Only variant IDs and quantities are stored, never prices.
 */

const STORAGE_KEY = "grademax.cart.v1"
export const CART_EVENT = "grademax:cart-changed"
const MAX_LINES = 20

export interface CartLine {
  variantId: string
  quantity: number
}

interface StoredCart {
  /** The account the cart was filled under, or null for a signed-out guest. */
  owner: string | null
  lines: CartLine[]
}

const EMPTY: StoredCart = { owner: null, lines: [] }

function isCartLine(l: unknown): l is CartLine {
  return typeof l === "object" && l !== null &&
    typeof (l as CartLine).variantId === "string" &&
    Number.isInteger((l as CartLine).quantity) && (l as CartLine).quantity > 0
}

function cleanLines(raw: unknown): CartLine[] {
  return Array.isArray(raw) ? raw.filter(isCartLine).slice(0, MAX_LINES) : []
}

function readStored(): StoredCart {
  if (typeof window === "undefined") return EMPTY
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return EMPTY
    const parsed: unknown = JSON.parse(raw)
    // Carts written before ownership existed are a bare array. Their owner is
    // unknown, so they are treated as a guest cart.
    if (Array.isArray(parsed)) return { owner: null, lines: cleanLines(parsed) }
    if (typeof parsed !== "object" || parsed === null) return EMPTY
    const owner = (parsed as StoredCart).owner
    return {
      owner: typeof owner === "string" ? owner : null,
      lines: cleanLines((parsed as StoredCart).lines),
    }
  } catch {
    // Private browsing and blocked site data both throw here. An empty cart is
    // the right answer — it must never take the page down.
    return EMPTY
  }
}

function writeStored(cart: StoredCart): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cart))
  } catch {
    // Storage unavailable: the cart stays in memory for this page view.
  }
  window.dispatchEvent(new CustomEvent(CART_EVENT))
}

export function readCartLines(): CartLine[] {
  return readStored().lines
}

/** Replace the lines, keeping the current owner. */
export function writeCartLines(lines: CartLine[]): void {
  writeStored({ owner: readStored().owner, lines })
}

/**
 * Make the stored cart agree with who is signed in. Call it only once the auth
 * state is known — calling it with null during the initial load would empty a
 * signed-in buyer's cart before their session had been read.
 */
export function reconcileCartOwner(userId: string | null): void {
  if (typeof window === "undefined") return
  const stored = readStored()

  if (userId === null) {
    if (stored.owner !== null) writeStored(EMPTY)
    return
  }
  if (stored.owner === userId) return
  if (stored.owner === null) {
    writeStored({ owner: userId, lines: stored.lines })
    return
  }
  writeStored({ owner: userId, lines: [] })
}
