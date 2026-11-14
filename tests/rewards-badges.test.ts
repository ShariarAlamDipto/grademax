import { test } from "node:test"
import assert from "node:assert/strict"
import {
  BADGE_TRACKS, evaluateBadge, evaluateBadges, experiencePoints, levelFor, xpForLevel, type RewardStats,
} from "../src/lib/rewards/badges"
import {
  completionPoints, longestStreakDays, percentageOf, summariseCompletions, weekStartUtc, type Completion,
} from "../src/lib/rewards/points"

const EMPTY: RewardStats = {
  questionsGenerated: 0, worksheetsMade: 0, testsBuilt: 0,
  papersLogged: 0, paperPoints: 0, papersScored: 0, bestPercentage: null, averagePercentage: null,
  timedPapers: 0, mostPapersInOneSubject: 0, longestStreakDays: 0, subjectsEnrolled: 0,
  questionsSolved: null, contributions: null,
}
const track = (id: string) => BADGE_TRACKS.find(t => t.id === id)!
const done = (subjectId: string, day: string, percentage: number | null = null, timed = false): Completion =>
  ({ subjectId, completedAt: `${day}T10:00:00Z`, percentage, timed })

// ── Badges ──────────────────────────────────────────────────────────────────

test("a new student has no tiers and zero XP", () => {
  const badges = evaluateBadges(EMPTY)
  assert.equal(badges.length, BADGE_TRACKS.length)
  assert.ok(badges.every(b => b.tier === null))
  assert.equal(experiencePoints(EMPTY), 0)
  assert.deepEqual(levelFor(0), { level: 1, title: "Starter", xp: 0, levelStart: 0, nextLevelAt: 100, progress: 0 })
})

test("badge ids are unique and thresholds rise", () => {
  assert.equal(new Set(BADGE_TRACKS.map(t => t.id)).size, BADGE_TRACKS.length)
  for (const t of BADGE_TRACKS) {
    assert.ok(t.thresholds.every((v, i) => i === 0 || v > t.thresholds[i - 1]), t.id)
  }
})

test("tiers are reached exactly at their thresholds", () => {
  const t = track("question-collector")
  assert.equal(evaluateBadge(t, { ...EMPTY, questionsGenerated: 49 }).tier, null)
  assert.equal(evaluateBadge(t, { ...EMPTY, questionsGenerated: 50 }).tier, "bronze")
  assert.equal(evaluateBadge(t, { ...EMPTY, questionsGenerated: 250 }).tier, "silver")
  assert.equal(evaluateBadge(t, { ...EMPTY, questionsGenerated: 1000 }).tier, "gold")
  assert.equal(evaluateBadge(t, { ...EMPTY, questionsGenerated: 5000 }).tier, "platinum")
})

test("progress runs from the last tier to the next one", () => {
  const b = evaluateBadge(track("question-collector"), { ...EMPTY, questionsGenerated: 150 })
  assert.equal(b.tier, "bronze")
  assert.equal(b.nextTier, "silver")
  assert.equal(b.nextThreshold, 250)
  assert.equal(b.progress, 0.5)
})

test("platinum is complete with no next tier", () => {
  const b = evaluateBadge(track("sheet-smith"), { ...EMPTY, worksheetsMade: 999 })
  assert.equal(b.tier, "platinum")
  assert.equal(b.nextTier, null)
  assert.equal(b.progress, 1)
})

test("tracks whose data is not recorded yet are marked unavailable", () => {
  assert.equal(evaluateBadge(track("problem-solver"), EMPTY).available, false)
  assert.equal(evaluateBadge(track("problem-solver"), { ...EMPTY, questionsSolved: 30 }).tier, "bronze")
})

test("the average badge needs three scored papers", () => {
  const two = { ...EMPTY, papersLogged: 9, papersScored: 2, averagePercentage: 95, bestPercentage: 95 }
  assert.equal(evaluateBadge(track("steady-hand"), two).tier, null)
  assert.equal(evaluateBadge(track("steady-hand"), { ...two, papersScored: 3 }).tier, "platinum")
  assert.equal(evaluateBadge(track("a-star-chaser"), two).tier, "platinum")
})

test("paper, subject, timed and streak badges read their own counts", () => {
  const stats = { ...EMPTY, papersLogged: 12, mostPapersInOneSubject: 6, timedPapers: 1, longestStreakDays: 7 }
  assert.equal(evaluateBadge(track("paper-finisher"), stats).tier, "silver")
  assert.equal(evaluateBadge(track("subject-specialist"), stats).tier, "bronze")
  assert.equal(evaluateBadge(track("exam-conditions"), stats).tier, "bronze")
  assert.equal(evaluateBadge(track("on-a-roll"), stats).tier, "silver")
})

// ── XP and levels ───────────────────────────────────────────────────────────

test("XP adds paper points to the weighted activity counts", () => {
  assert.equal(experiencePoints({ ...EMPTY, questionsGenerated: 30, worksheetsMade: 1 }), 40)
  assert.equal(experiencePoints({ ...EMPTY, paperPoints: 55 }), 55)
  assert.equal(experiencePoints({ ...EMPTY, questionsSolved: 10, contributions: 1, testsBuilt: 2 }), 110)
})

test("levels start at 0, 100, 300, 600 XP", () => {
  assert.deepEqual([1, 2, 3, 4].map(xpForLevel), [0, 100, 300, 600])
  assert.equal(levelFor(99).level, 1)
  assert.equal(levelFor(100).level, 2)
  assert.equal(levelFor(299).level, 2)
  assert.equal(levelFor(300).level, 3)
  assert.equal(levelFor(200).progress, 0.5)
})

test("level titles stop at the last name", () => {
  assert.equal(levelFor(1_000_000).title, "A* Legend")
  assert.equal(levelFor(-5).level, 1)
})

// ── Progression points ──────────────────────────────────────────────────────

test("a completed paper earns 20, plus up to 30 for the score, plus 5 if timed", () => {
  assert.equal(completionPoints(null, false), 20)
  assert.equal(completionPoints(null, true), 25)
  assert.equal(completionPoints(0, false), 20)
  assert.equal(completionPoints(50, false), 35)
  assert.equal(completionPoints(100, false), 50)
  assert.equal(completionPoints(100, true), 55)
  assert.equal(completionPoints(83.3, false), 45)
})

test("out-of-range scores are clamped", () => {
  assert.equal(completionPoints(140, false), 50)
  assert.equal(completionPoints(-20, false), 20)
})

test("percentage needs both numbers and a positive maximum", () => {
  assert.equal(percentageOf(45, 60), 75)
  assert.equal(percentageOf(50, 75), 66.7)
  assert.equal(percentageOf(80, 60), 100)
  assert.equal(percentageOf(null, 60), null)
  assert.equal(percentageOf(10, null), null)
  assert.equal(percentageOf(10, 0), null)
  assert.equal(percentageOf(-1, 60), null)
  assert.equal(percentageOf(Number.NaN, 60), null)
})

test("streaks count consecutive days, ignoring repeats on one day", () => {
  assert.equal(longestStreakDays([]), 0)
  assert.equal(longestStreakDays(["2026-11-01T08:00:00Z", "2026-11-01T20:00:00Z"]), 1)
  assert.equal(longestStreakDays([
    "2026-11-03T09:00:00Z", "2026-11-01T09:00:00Z", "2026-11-02T09:00:00Z", // 3 in a row, unordered
    "2026-11-06T09:00:00Z", "2026-11-07T09:00:00Z",
  ]), 3)
  // Across a month boundary.
  assert.equal(longestStreakDays(["2026-10-31T23:00:00Z", "2026-11-01T01:00:00Z"]), 2)
})

test("completions are summarised into the facts the badges use", () => {
  assert.deepEqual(summariseCompletions([]), {
    papersCompleted: 0, paperPoints: 0, bestPercentage: null, averagePercentage: null,
    timedPapers: 0, mostPapersInOneSubject: 0, longestStreakDays: 0, bySubject: {},
  })
  const summary = summariseCompletions([
    done("phy", "2026-11-01", 60),
    done("phy", "2026-11-02", 90, true),
    done("phy", "2026-11-04"),
    done("che", "2026-11-04", 75),
  ])
  assert.equal(summary.papersCompleted, 4)
  assert.equal(summary.bestPercentage, 90)
  assert.equal(summary.averagePercentage, 75)
  assert.equal(summary.timedPapers, 1)
  assert.equal(summary.mostPapersInOneSubject, 3)
  assert.equal(summary.longestStreakDays, 2)
  // phy: 38 + 52 + 20; che: 43 (22.5 rounds to 23)
  assert.deepEqual(summary.bySubject, { phy: { papers: 3, points: 110 }, che: { papers: 1, points: 43 } })
  assert.equal(summary.paperPoints, 153)
})

test("the leaderboard week starts on Monday 00:00 UTC", () => {
  assert.equal(weekStartUtc(new Date("2026-11-14T10:30:00Z")).toISOString(), "2026-11-09T00:00:00.000Z")
  assert.equal(weekStartUtc(new Date("2026-11-09T00:00:00Z")).toISOString(), "2026-11-09T00:00:00.000Z")
  assert.equal(weekStartUtc(new Date("2026-11-15T23:59:00Z")).toISOString(), "2026-11-09T00:00:00.000Z")
})
