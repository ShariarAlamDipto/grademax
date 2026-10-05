import { test } from "node:test"
import assert from "node:assert/strict"
import { pageWindow } from "../src/lib/pagination"
import { parseQuestionCount } from "../src/lib/questionCountInput"
import { parseStoredBasket, serializeBasket } from "../src/lib/basketStorage"

// ── pageWindow ──────────────────────────────────────────────

test("pageWindow lists every page when they all fit", () => {
  assert.deepEqual(pageWindow(1, 3, 7), [1, 2, 3])
})

test("pageWindow keeps the window pinned at the start and end", () => {
  assert.deepEqual(pageWindow(2, 20, 5), [1, 2, 3, 4, 5])
  assert.deepEqual(pageWindow(19, 20, 5), [16, 17, 18, 19, 20])
})

test("pageWindow centres the current page in the middle", () => {
  assert.deepEqual(pageWindow(10, 20, 5), [8, 9, 10, 11, 12])
  assert.deepEqual(pageWindow(10, 20, 7), [7, 8, 9, 10, 11, 12, 13])
})

test("pageWindow handles no pages", () => {
  assert.deepEqual(pageWindow(1, 0, 5), [])
})

// ── parseQuestionCount ──────────────────────────────────────

test("parseQuestionCount clamps to the allowed range", () => {
  assert.equal(parseQuestionCount("15", 30, 20), 15)
  assert.equal(parseQuestionCount("99", 30, 20), 30)
  assert.equal(parseQuestionCount("0", 30, 20), 1)
  assert.equal(parseQuestionCount("-4", 30, 20), 1)
})

test("parseQuestionCount falls back for empty or junk input", () => {
  assert.equal(parseQuestionCount("", 30, 20), 20)
  assert.equal(parseQuestionCount("abc", 30, 20), 20)
})

test("parseQuestionCount keeps the fallback inside the range", () => {
  assert.equal(parseQuestionCount("", 10, 20), 10)
})

// ── basket storage ──────────────────────────────────────────

const item = {
  id: "q1",
  questionNumber: "3",
  topics: ["1.2"],
  difficulty: "easy",
  qpPageUrl: "https://example.com/q1.pdf",
  msPageUrl: null,
  hasDiagram: false,
  textExcerpt: "",
  year: 2021,
  season: "Jun",
  paper: "1",
}

test("a saved basket round-trips", () => {
  const raw = serializeBasket({ subjectId: "s1", title: "Mock", items: [item] })
  assert.deepEqual(parseStoredBasket(raw), { subjectId: "s1", title: "Mock", items: [item] })
})

test("missing or corrupt storage yields null", () => {
  assert.equal(parseStoredBasket(null), null)
  assert.equal(parseStoredBasket("{not json"), null)
  assert.equal(parseStoredBasket(JSON.stringify({ subjectId: 5 })), null)
  assert.equal(parseStoredBasket(JSON.stringify({ subjectId: "s1", title: "x", items: "no" })), null)
})

test("malformed items are dropped, valid ones kept", () => {
  const raw = JSON.stringify({
    subjectId: "s1",
    title: "x",
    items: [item, { id: "q2" }, null, { ...item, qpPageUrl: 7 }],
  })
  assert.deepEqual(parseStoredBasket(raw)?.items, [item])
})
