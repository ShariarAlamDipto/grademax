import { test } from "node:test"
import assert from "node:assert/strict"
import { searchCatalogue, type SearchableBook } from "../src/lib/store/catalogueSearch"
import { wheelSlots, wrapIndex } from "../src/lib/store/bookWheel"

const book = (title: string, subjectCode: string, kind: SearchableBook["kind"], level = "IGCSE"): SearchableBook =>
  ({ title, subtitle: null, subjectCode, spec: null, level, kind })

const BOOKS = [
  book("Physics Yearwise 2026", "4PH1", "yearwise"),
  book("Further Pure Mathematics Workbook", "4PM1", "workbook"),
  book("Mechanics 1 Yearwise", "WME01", "yearwise", "IAL"),
  book("Mathematics B", "4MB1", "workbook"),
]

test("an empty query returns every book", () => {
  assert.equal(searchCatalogue(BOOKS, "  ").length, 4)
})

test("matches by subject name, case-insensitively", () => {
  assert.deepEqual(searchCatalogue(BOOKS, "PHYSICS").map(b => b.subjectCode), ["4PH1"])
})

test("matches by subject code", () => {
  assert.deepEqual(searchCatalogue(BOOKS, "4mb1").map(b => b.subjectCode), ["4MB1"])
})

test("every word must match", () => {
  assert.deepEqual(searchCatalogue(BOOKS, "yearwise mechanics").map(b => b.subjectCode), ["WME01"])
  assert.equal(searchCatalogue(BOOKS, "physics workbook").length, 0)
})

test("unit shorthand m1 finds Mechanics 1 and not 4PM1", () => {
  assert.deepEqual(searchCatalogue(BOOKS, "m1").map(b => b.subjectCode), ["WME01"])
})

test("kind words find booklets and workbooks", () => {
  assert.equal(searchCatalogue(BOOKS, "booklet").length, 2)
  assert.equal(searchCatalogue(BOOKS, "chapterwise").length, 2)
})

test("level words find IAL books", () => {
  assert.deepEqual(searchCatalogue(BOOKS, "a level").map(b => b.subjectCode), ["WME01"])
})

test("wrapIndex loops in both directions", () => {
  assert.equal(wrapIndex(0, 5), 0)
  assert.equal(wrapIndex(5, 5), 0)
  assert.equal(wrapIndex(7, 5), 2)
  assert.equal(wrapIndex(-1, 5), 4)
  assert.equal(wrapIndex(-11, 5), 4)
})

test("the wheel draws the centre book and its neighbours, looping past the ends", () => {
  const slots = wheelSlots(0, 4, 2)
  assert.deepEqual(slots.map(s => s.index), [2, 3, 0, 1, 2])
  assert.deepEqual(slots.map(s => s.offset), [-2, -1, 0, 1, 2])
})

test("a part-turned wheel keeps stable keys and fractional offsets", () => {
  const slots = wheelSlots(10.25, 57, 1)
  assert.deepEqual(slots.map(s => s.key), [9, 10, 11])
  assert.deepEqual(slots.map(s => s.offset), [-1.25, -0.25, 0.75])
  // Turning backwards past zero still lands on real books.
  assert.deepEqual(wheelSlots(-1, 57, 1).map(s => s.index), [55, 56, 0])
})

test("an empty catalogue draws nothing", () => {
  assert.deepEqual(wheelSlots(3, 0, 3), [])
})
