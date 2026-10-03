import { test } from "node:test"
import assert from "node:assert/strict"
import {
  MAX_QUESTIONS_PER_PAPER,
  exceedsLimit,
  isProActive,
  questionLimitFor,
} from "../src/lib/toolLimits"

const NOW = Date.parse("2026-10-03T12:00:00Z")
const DAY = 24 * 60 * 60 * 1000
const iso = (ms: number) => new Date(ms).toISOString()

test("a normal student is capped at 30", () => {
  assert.equal(MAX_QUESTIONS_PER_PAPER, 30)
  assert.equal(questionLimitFor({ role: "student" }, NOW), 30)
  assert.equal(questionLimitFor({}, NOW), 30)
})

test("admins, teachers and the super admin have no limit", () => {
  assert.equal(questionLimitFor({ role: "admin" }, NOW), null)
  assert.equal(questionLimitFor({ role: "teacher" }, NOW), null)
  assert.equal(questionLimitFor({ role: "student", superAdmin: true }, NOW), null)
})

test("a student with an active Pro pack has no limit", () => {
  assert.equal(questionLimitFor({ role: "student", proUntil: iso(NOW + DAY) }, NOW), null)
})

test("an expired, missing or malformed Pro pack keeps the limit", () => {
  assert.equal(questionLimitFor({ role: "student", proUntil: iso(NOW - 1) }, NOW), 30)
  assert.equal(questionLimitFor({ role: "student", proUntil: iso(NOW) }, NOW), 30)
  assert.equal(questionLimitFor({ role: "student", proUntil: null }, NOW), 30)
  assert.equal(isProActive("not a date", NOW), false)
})

test("exceedsLimit allows exactly the limit and ignores unlimited", () => {
  assert.equal(exceedsLimit(30, 30), false)
  assert.equal(exceedsLimit(31, 30), true)
  assert.equal(exceedsLimit(500, null), false)
})
