/**
 * Rewards: badge tracks, tiers, experience points and levels.
 *
 * Pure functions over a student's activity counts, so the rules can be unit
 * tested and shown identically on the dashboard and the profile. Nothing here
 * reads the database; see ./stats.ts for that.
 */

export interface RewardStats {
  /** Questions placed into worksheets and tests the student generated. */
  questionsGenerated: number
  worksheetsMade: number
  testsBuilt: number
  /** Papers ticked as completed on the dashboard. */
  papersLogged: number
  /** Progression points earned by those papers (see ./points.ts). */
  paperPoints: number
  /** Papers with a score entered: averages are judged on these. */
  papersScored: number
  /** Best saved percentage, or null when no score is saved. */
  bestPercentage: number | null
  /** Mean saved percentage, or null when no score is saved. */
  averagePercentage: number | null
  /** Papers sat under exam conditions. */
  timedPapers: number
  /** Most papers completed in any one subject. */
  mostPapersInOneSubject: number
  /** Longest run of consecutive days with a completed paper. */
  longestStreakDays: number
  /** Subjects on the student's list. */
  subjectsEnrolled: number
  /** null = solve tracking is not switched on yet (migration 45). */
  questionsSolved: number | null
  /** null = community contributions are not switched on yet (migration 45). */
  contributions: number | null
}

export type Tier = "bronze" | "silver" | "gold" | "platinum"
export const TIERS: readonly Tier[] = ["bronze", "silver", "gold", "platinum"]

export type BadgeGlyph =
  | "stack" | "sheet" | "blueprint" | "stopwatch" | "star" | "pulse" | "check" | "hands"
  | "medal" | "flame" | "clipboard"

export interface BadgeTrack {
  id: string
  title: string
  /** What the number counts, e.g. "questions generated". */
  unit: string
  glyph: BadgeGlyph
  /** Value needed for bronze, silver, gold, platinum. */
  thresholds: readonly [number, number, number, number]
  /** Reads the track's value; null means the track is not available yet. */
  value: (stats: RewardStats) => number | null
}

/** Averages only mean something after a few papers. */
export const MIN_PAPERS_FOR_AVERAGE = 3

export const BADGE_TRACKS: readonly BadgeTrack[] = [
  { id: "question-collector", title: "Question Collector", unit: "questions generated", glyph: "stack",
    thresholds: [50, 250, 1000, 5000], value: s => s.questionsGenerated },
  { id: "sheet-smith", title: "Sheet Smith", unit: "worksheets made", glyph: "sheet",
    thresholds: [1, 10, 50, 200], value: s => s.worksheetsMade },
  { id: "test-architect", title: "Test Architect", unit: "tests built", glyph: "blueprint",
    thresholds: [1, 5, 25, 100], value: s => s.testsBuilt },
  { id: "paper-finisher", title: "Paper Finisher", unit: "papers completed", glyph: "clipboard",
    thresholds: [1, 10, 30, 75], value: s => s.papersLogged },
  { id: "subject-specialist", title: "Subject Specialist", unit: "papers in one subject", glyph: "medal",
    thresholds: [5, 15, 30, 60], value: s => s.mostPapersInOneSubject },
  { id: "exam-conditions", title: "Exam Conditions", unit: "timed papers", glyph: "stopwatch",
    thresholds: [1, 5, 15, 40], value: s => s.timedPapers },
  { id: "on-a-roll", title: "On a Roll", unit: "days in a row", glyph: "flame",
    thresholds: [3, 7, 14, 30], value: s => s.longestStreakDays },
  { id: "a-star-chaser", title: "A* Chaser", unit: "% best paper", glyph: "star",
    thresholds: [60, 75, 90, 95], value: s => s.bestPercentage ?? 0 },
  { id: "steady-hand", title: "Steady Hand", unit: "% average over 3+ papers", glyph: "pulse",
    thresholds: [50, 65, 80, 90],
    value: s => (s.papersScored >= MIN_PAPERS_FOR_AVERAGE ? s.averagePercentage ?? 0 : 0) },
  { id: "problem-solver", title: "Problem Solver", unit: "questions solved", glyph: "check",
    thresholds: [25, 100, 500, 2000], value: s => s.questionsSolved },
  { id: "community-builder", title: "Community Builder", unit: "accepted contributions", glyph: "hands",
    thresholds: [1, 5, 20, 50], value: s => s.contributions },
]

export interface BadgeProgress {
  track: BadgeTrack
  /** false when the track's data is not being recorded yet. */
  available: boolean
  value: number
  /** Highest tier reached, or null. */
  tier: Tier | null
  /** Next tier's threshold, or null at platinum. */
  nextThreshold: number | null
  nextTier: Tier | null
  /** 0–1 towards the next tier (1 at platinum). */
  progress: number
}

export function evaluateBadge(track: BadgeTrack, stats: RewardStats): BadgeProgress {
  const raw = track.value(stats)
  const available = raw !== null
  const value = Math.max(0, raw ?? 0)
  const reached = track.thresholds.filter(t => value >= t).length
  const tier = reached > 0 ? TIERS[reached - 1] : null
  const nextThreshold = reached < TIERS.length ? track.thresholds[reached] : null
  const previous = reached > 0 ? track.thresholds[reached - 1] : 0
  const progress = nextThreshold === null
    ? 1
    : Math.min(1, Math.max(0, (value - previous) / (nextThreshold - previous)))
  return { track, available, value, tier, nextThreshold, nextTier: nextThreshold === null ? null : TIERS[reached], progress }
}

export function evaluateBadges(stats: RewardStats): BadgeProgress[] {
  return BADGE_TRACKS.map(track => evaluateBadge(track, stats))
}

/**
 * Experience points. Completed papers bring their own progression points
 * (20–55 each); everything else has a fixed weight, kept low for actions that
 * cost only a click.
 */
export const XP_WEIGHTS = {
  questionGenerated: 1,
  worksheetMade: 10,
  testBuilt: 15,
  questionSolved: 3,
  contribution: 50,
} as const

export function experiencePoints(stats: RewardStats): number {
  return (
    stats.questionsGenerated * XP_WEIGHTS.questionGenerated +
    stats.worksheetsMade * XP_WEIGHTS.worksheetMade +
    stats.testsBuilt * XP_WEIGHTS.testBuilt +
    stats.paperPoints +
    (stats.questionsSolved ?? 0) * XP_WEIGHTS.questionSolved +
    (stats.contributions ?? 0) * XP_WEIGHTS.contribution
  )
}

const LEVEL_TITLES = ["Starter", "Learner", "Practitioner", "Scholar", "Expert", "Master", "A* Legend"] as const
const XP_STEP = 100

/** XP needed to reach a level: 0, 100, 300, 600, 1000 … (each level costs 100 more). */
export function xpForLevel(level: number): number {
  return (XP_STEP * (level - 1) * level) / 2
}

export interface LevelInfo {
  level: number
  title: string
  xp: number
  /** XP at which this level started and the next one starts. */
  levelStart: number
  nextLevelAt: number
  /** 0–1 through the current level. */
  progress: number
}

export function levelFor(xp: number): LevelInfo {
  const safe = Math.max(0, Math.floor(xp))
  const level = Math.floor((1 + Math.sqrt(1 + (8 * safe) / XP_STEP)) / 2)
  const levelStart = xpForLevel(level)
  const nextLevelAt = xpForLevel(level + 1)
  return {
    level,
    title: LEVEL_TITLES[Math.min(level - 1, LEVEL_TITLES.length - 1)],
    xp: safe,
    levelStart,
    nextLevelAt,
    progress: (safe - levelStart) / (nextLevelAt - levelStart),
  }
}
