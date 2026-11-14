import Link from "next/link"
import { BadgeIcon } from "./BadgeIcon"
import { evaluateBadges, experiencePoints, levelFor, type BadgeProgress } from "@/lib/rewards/badges"
import type { LeaderboardRow, RecentResult, RewardsData } from "@/lib/rewards/stats"
import "./rewards.css"

/**
 * The student's progress at a glance: level, counts, badges, the weekly
 * all-subject leaderboard and community contributions. A server component: it only renders the
 * data handed to it.
 */

const number = new Intl.NumberFormat("en-GB")

function tierLabel(badge: BadgeProgress): string {
  if (!badge.available) return "Coming soon"
  if (!badge.tier) return "Not earned yet"
  return badge.tier.charAt(0).toUpperCase() + badge.tier.slice(1)
}

function progressLabel(badge: BadgeProgress): string {
  if (!badge.available) return "Tracking for this badge is not switched on yet."
  const value = number.format(Math.floor(badge.value))
  if (badge.nextThreshold === null) return `${value} ${badge.track.unit} — top tier reached`
  return `${value} / ${number.format(badge.nextThreshold)} ${badge.track.unit} for ${badge.nextTier}`
}

function LevelRing({ level, progress }: { level: number; progress: number }) {
  const circumference = 2 * Math.PI * 34
  return (
    <div className="rw-ring" role="img" aria-label={`Level ${level}, ${Math.round(progress * 100)}% of the way to the next level`}>
      <svg viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--gm-surface-3)" strokeWidth="7" />
        <circle
          cx="40" cy="40" r="34" fill="none" stroke="var(--gm-amber)" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${progress * circumference} ${circumference}`} transform="rotate(-90 40 40)"
        />
      </svg>
      <span><small>Level</small>{level}</span>
    </div>
  )
}

function RecentChart({ results }: { results: RecentResult[] }) {
  if (results.length === 0) {
    return (
      <p className="rw-empty">
        No scores saved yet. Tick a paper as completed under “My subjects” and enter your score — it will appear here.
      </p>
    )
  }
  return (
    <ol className="rw-bars" aria-label="Your latest saved results">
      {results.map((r, i) => (
        <li key={`${r.label}-${i}`}>
          <b>{r.percentage}%</b>
          <span className="rw-bar"><i style={{ height: `${Math.max(r.percentage, 3)}%` }} /></span>
          <small title={r.label}>{r.label}</small>
        </li>
      ))}
    </ol>
  )
}

function BattleTable({ rows }: { rows: LeaderboardRow[] }) {
  if (rows.length === 0) {
    return <p className="rw-empty">Nobody has completed a paper this week yet. Finish one to take first place.</p>
  }
  return (
    <ol className="rw-battle" aria-label="This week's Marks Battle">
      {rows.map(row => (
        <li key={`${row.rank}-${row.displayName}`} data-me={row.isMe || undefined}>
          <span className="rw-rank">{row.rank}</span>
          <span className="rw-name">{row.isMe ? "You" : row.displayName}<small>{row.papers} {row.papers === 1 ? "paper" : "papers"}</small></span>
          <span className="rw-track"><i style={{ width: `${Math.max(4, Math.round((row.points / rows[0].points) * 100))}%` }} /></span>
          <b>{row.points} pts</b>
        </li>
      ))}
    </ol>
  )
}

const CONTRIBUTION_WAYS = [
  { title: "Report a wrong mark scheme", text: "Flag a question whose answer does not match it." },
  { title: "Suggest a chapter tag", text: "Tell us when a question sits under the wrong topic." },
  { title: "Share a worked solution", text: "Explain a hard question for the next student." },
  { title: "Point out a missing paper", text: "Help complete the past-paper library." },
]

export function RewardsPanel({ data }: { data: RewardsData }) {
  const { stats, recent, weekly, progressAvailable } = data
  const level = levelFor(experiencePoints(stats))
  const badges = evaluateBadges(stats)
  const earned = badges.filter(b => b.tier !== null).length

  const tiles: { label: string; value: string }[] = [
    { label: "Papers completed", value: progressAvailable ? number.format(stats.papersLogged) : "Soon" },
    { label: "Paper points", value: progressAvailable ? number.format(stats.paperPoints) : "Soon" },
    { label: "Best paper", value: stats.bestPercentage === null ? "—" : `${Math.round(stats.bestPercentage)}%` },
    { label: "Questions generated", value: number.format(stats.questionsGenerated) },
    { label: "Questions solved", value: stats.questionsSolved === null ? "Soon" : number.format(stats.questionsSolved) },
    { label: "Worksheets and tests", value: number.format(stats.worksheetsMade + stats.testsBuilt) },
  ]

  return (
    <section className="rw" aria-labelledby="rewards-title">
      <div className="rw-top">
        <LevelRing level={level.level} progress={level.progress} />
        <div className="rw-level">
          <p className="rw-eyebrow">Your progress</p>
          <h2 id="rewards-title">{level.title}</h2>
          <div className="rw-xp" aria-hidden><i style={{ width: `${level.progress * 100}%` }} /></div>
          <p className="rw-muted">
            {number.format(level.xp)} XP · {number.format(level.nextLevelAt - level.xp)} XP to level {level.level + 1} ·{" "}
            {earned} of {badges.length} badges earned
          </p>
        </div>
      </div>

      <dl className="rw-tiles">
        {tiles.map(tile => (
          <div key={tile.label}>
            <dt>{tile.label}</dt>
            <dd>{tile.value}</dd>
          </div>
        ))}
      </dl>

      <h3 className="rw-heading">Badges</h3>
      <ul className="rw-badges">
        {badges.map(badge => (
          <li key={badge.track.id} data-earned={badge.tier ? "" : undefined} data-soon={badge.available ? undefined : ""}>
            <BadgeIcon id={badge.track.id} glyph={badge.track.glyph} tier={badge.tier} size={52} />
            <div className="rw-badge-text">
              <b>{badge.track.title}</b>
              <span className="rw-tier" data-tier={badge.tier ?? "none"}>{tierLabel(badge)}</span>
              <span className="rw-progress" aria-hidden><i style={{ width: `${badge.available ? badge.progress * 100 : 0}%` }} /></span>
              <small>{progressLabel(badge)}</small>
            </div>
          </li>
        ))}
      </ul>

      <div className="rw-two">
        <div className="rw-card">
          <h3 className="rw-heading">Marks Battle</h3>
          {weekly ? (
            <>
              <p className="rw-muted">
                This week&apos;s ranking across every subject, by progression points. Resets every Monday. Each subject
                has its own leaderboard under “My subjects”.
              </p>
              <BattleTable rows={weekly} />
              {recent.length > 0 ? (
                <>
                  <h4 className="rw-subheading">Your latest scores</h4>
                  <RecentChart results={recent} />
                </>
              ) : null}
            </>
          ) : (
            <p className="rw-empty">
              The weekly Marks Battle switches on with the dashboard database update. Points from completed papers
              will rank you here and on each subject&apos;s own leaderboard.
            </p>
          )}
        </div>

        <div className="rw-card">
          <h3 className="rw-heading">Community contributions</h3>
          <p className="rw-muted">
            {stats.contributions === null
              ? "Planned: earn the Community Builder badge by helping other students. Each accepted contribution is worth 50 XP."
              : `${number.format(stats.contributions)} accepted so far. Each one is worth 50 XP.`}
          </p>
          <ul className="rw-ways">
            {CONTRIBUTION_WAYS.map(way => (
              <li key={way.title}><b>{way.title}</b><span>{way.text}</span></li>
            ))}
          </ul>
          <Link href="/improvements" className="rw-link">Send a suggestion today →</Link>
        </div>
      </div>
    </section>
  )
}
