import { test } from "node:test"
import assert from "node:assert/strict"
import { SHELF_FILTERS, levelOf, kindOf, parseShelfFilter, shelve } from "../src/lib/store/shelves"

const p = (slug: string, subject_code: string | null) => ({ slug, subject_code })

test("level comes from the Pearson code", () => {
  assert.equal(levelOf(p("x", "4MA1")), "IGCSE")
  assert.equal(levelOf(p("x", "WPH11")), "IAL")
  assert.equal(levelOf(p("x", null)), "Other")
})

test("yearwise booklets are told apart from chapterwise workbooks", () => {
  assert.equal(kindOf(p("wph11-yearwise-2026", "WPH11")), "yearwise")
  assert.equal(kindOf(p("m1-yearwise", "WME01")), "yearwise")
  assert.equal(kindOf(p("mathematics-b", "4MB1")), "workbook")
})

test("an unknown filter falls back to all", () => {
  assert.equal(parseShelfFilter(undefined), "all")
  assert.equal(parseShelfFilter("ial"), "ial")
  assert.equal(parseShelfFilter(["yearwise"]), "yearwise")
  assert.equal(parseShelfFilter("<script>"), "all")
  assert.deepEqual(SHELF_FILTERS.map(f => f.key), ["all", "igcse", "ial", "yearwise", "workbook"])
})

test("shelves keep the catalogue order and drop empty groups", () => {
  const items = [
    p("mathematics-b", "4MB1"), p("4ma1-yearwise-2026", "4MA1"),
    p("wph11-yearwise-2026", "WPH11"), p("wme01-yearwise-2026", "WME01"),
  ]
  const all = shelve(items, "all")
  assert.deepEqual(all.map(s => s.title), ["IGCSE", "International A Level (IAL)"])
  assert.deepEqual(all[0].items.map(i => i.slug), ["mathematics-b", "4ma1-yearwise-2026"])

  const ial = shelve(items, "ial")
  assert.equal(ial.length, 1)
  assert.equal(ial[0].items.length, 2)

  const workbooks = shelve(items, "workbook")
  assert.deepEqual(workbooks.flatMap(s => s.items.map(i => i.slug)), ["mathematics-b"])
})
