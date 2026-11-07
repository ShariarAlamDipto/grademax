import { test } from "node:test"
import assert from "node:assert/strict"
import { USAGE_FEATURES, fromUsageSummary } from "../src/lib/usageReport"

const summary = {
  first_day: "2026-10-08",
  totals: [{ feature: "paper_view", count: 12 }, { feature: "worksheet_generate", count: 5 }],
  users: [{ feature: "worksheet_generate", users: 3 }],
  daily: [
    { date: "2026-11-05", feature: "paper_view", count: 4 },
    { date: "2026-11-06", feature: "paper_view", count: 5 },
    { date: "2026-11-06", feature: "worksheet_generate", count: 2 },
  ],
  subjects: [
    { feature: "paper_view", subject: "Unknown", count: 7 },
    { feature: "paper_view", subject: "Physics", count: 5 },
    { feature: "worksheet_generate", subject: "Physics", count: 3 },
    { feature: "worksheet_download", subject: "Biology", count: 9 },
    { feature: "test_builder_session", subject: "Physics", count: 1 },
  ],
  papers: [{ title: "Physics 2023 June Paper 1", total: 12, last30: 5 }],
}

test("totals and unique users cover every feature, 0 when missing", () => {
  const r = fromUsageSummary(summary)
  assert.equal(r.totals.paper_view, 12)
  assert.equal(r.totals.lecture_view, 0)
  assert.equal(r.uniqueUsers.worksheet_generate, 3)
  assert.equal(r.uniqueUsers.paper_view, 0)
  assert.deepEqual(Object.keys(r.totals).sort(), [...USAGE_FEATURES].sort())
})

test("daily rows have one column per feature, oldest first", () => {
  const r = fromUsageSummary(summary)
  assert.deepEqual(r.daily.map(d => d.date), ["2026-11-05", "2026-11-06"])
  assert.equal(r.daily[1].paper_view, 5)
  assert.equal(r.daily[1].worksheet_generate, 2)
  assert.equal(r.daily[0].worksheet_generate, 0)
})

test("tool subjects are grouped per tool and sorted by total, busiest first", () => {
  const r = fromUsageSummary(summary)
  assert.deepEqual(Object.keys(r.worksheetBySubject), ["Biology", "Physics"])
  assert.deepEqual(r.worksheetBySubject.Physics, { worksheet_generate: 3, worksheet_download: 0 })
  assert.deepEqual(r.testBuilderBySubject.Physics, { test_builder_session: 1, test_builder_download: 0 })
})

test("paper views by subject and top papers pass through, sorted", () => {
  const r = fromUsageSummary(summary)
  assert.deepEqual(r.paperViewsBySubject, [{ subject: "Unknown", views: 7 }, { subject: "Physics", views: 5 }])
  assert.deepEqual(r.topPapers, [{ title: "Physics 2023 June Paper 1", total: 12, last30: 5 }])
  assert.equal(r.source, "summary")
})

test("junk input does not throw", () => {
  const r = fromUsageSummary({ totals: null, daily: "x", subjects: [{ feature: "nope", subject: 1, count: "a" }] })
  assert.equal(r.totals.paper_view, 0)
  assert.deepEqual(r.daily, [])
  assert.deepEqual(r.paperViewsBySubject, [])
})
