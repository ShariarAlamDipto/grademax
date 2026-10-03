import { test, beforeEach } from "node:test"
import assert from "node:assert/strict"

// A minimal browser: localStorage plus the event dispatch cartStorage uses.
const store = new Map<string, string>()
const g = globalThis as unknown as { window: unknown; CustomEvent: unknown }
g.CustomEvent = class { constructor(public type: string) {} }
g.window = {
  localStorage: {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, v) },
  },
  dispatchEvent: () => true,
}

// cartStorage reads `window` only when called, so a static import is safe.
import { readCartLines, writeCartLines, reconcileCartOwner } from "../src/lib/store/cartStorage"

const LINE = { variantId: "v1", quantity: 2 }

beforeEach(() => store.clear())

test("a guest cart is adopted by whoever signs in", () => {
  writeCartLines([LINE])
  reconcileCartOwner("alice")
  assert.deepEqual(readCartLines(), [LINE])
})

test("the owner keeps their cart across reloads", () => {
  reconcileCartOwner("alice")
  writeCartLines([LINE])
  reconcileCartOwner("alice")
  assert.deepEqual(readCartLines(), [LINE])
})

test("a different account signing in does not see the previous cart", () => {
  reconcileCartOwner("alice")
  writeCartLines([LINE])
  reconcileCartOwner("bob")
  assert.deepEqual(readCartLines(), [])
})

test("signing out empties an owned cart", () => {
  reconcileCartOwner("alice")
  writeCartLines([LINE])
  reconcileCartOwner(null)
  assert.deepEqual(readCartLines(), [])
})

test("a signed-out guest keeps their own cart", () => {
  writeCartLines([LINE])
  reconcileCartOwner(null)
  assert.deepEqual(readCartLines(), [LINE])
})

test("a cart saved in the old bare-array format is read as a guest cart", () => {
  store.set("grademax.cart.v1", JSON.stringify([LINE]))
  assert.deepEqual(readCartLines(), [LINE])
  reconcileCartOwner("alice")
  assert.deepEqual(readCartLines(), [LINE])
})
