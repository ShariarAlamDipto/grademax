"use client"

import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import {
  NICKNAME_MAX, cleanNickname, getLeaderboardSettings, loadLeaderboard, saveLeaderboardSettings,
  type LeaderboardSettings, type SubjectOption,
} from "@/lib/dashboard/studentData"
import type { LeaderboardRow } from "@/lib/rewards/stats"
import { weekStartUtc } from "@/lib/rewards/points"

/**
 * One subject's leaderboard, ranked by progression points. A student appears
 * to others only after opting in, under a nickname of their choice.
 */

interface SubjectLeaderboardProps {
  userId: string
  subject: SubjectOption
}

type Period = "week" | "all"
type Status = "loading" | "ready" | "unavailable" | "error"

export function SubjectLeaderboard({ userId, subject }: SubjectLeaderboardProps) {
  const [period, setPeriod] = useState<Period>("week")
  const [rows, setRows] = useState<LeaderboardRow[]>([])
  const [status, setStatus] = useState<Status>("loading")
  const [settings, setSettings] = useState<LeaderboardSettings | null>(null)
  const [nickname, setNickname] = useState("")
  const [saving, setSaving] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let cancelled = false
    setStatus("loading")
    loadLeaderboard(supabase, subject.id, period === "week" ? weekStartUtc(new Date()) : null).then(result => {
      if (cancelled) return
      if (result.ok) { setRows(result.data); setStatus("ready") }
      else setStatus(result.unavailable ? "unavailable" : "error")
    })
    return () => { cancelled = true }
  }, [subject.id, period, reload])

  useEffect(() => {
    let cancelled = false
    getLeaderboardSettings(supabase, userId).then(result => {
      if (cancelled || !result.ok) return
      setSettings(result.data)
      setNickname(result.data.nickname)
    })
    return () => { cancelled = true }
  }, [userId])

  const saveSettings = async (optIn: boolean) => {
    const cleaned = cleanNickname(nickname)
    if (cleaned.error) { setNote(cleaned.error); return }
    setSaving(true)
    setNote(null)
    const result = await saveLeaderboardSettings(supabase, userId, { optIn, nickname })
    setSaving(false)
    if (!result.ok) { setNote("Your leaderboard setting could not be saved. Please try again."); return }
    setSettings({ optIn, nickname: cleaned.value ?? "" })
    setNote(optIn ? "You are on the leaderboard." : "You are hidden from other students.")
    setReload(n => n + 1)
  }

  if (status === "unavailable") {
    return (
      <p className="db-notice">
        The {subject.name} leaderboard switches on once the dashboard database update is applied. Points you earn
        after that will count from your first completed paper.
      </p>
    )
  }

  return (
    <div>
      <div className="db-lb-head">
        <div className="db-segment" role="group" aria-label="Leaderboard period">
          <button type="button" aria-pressed={period === "week"} onClick={() => setPeriod("week")}>This week</button>
          <button type="button" aria-pressed={period === "all"} onClick={() => setPeriod("all")}>All time</button>
        </div>
        <p className="db-muted">Ranked by progression points in {subject.name}.</p>
      </div>

      {settings ? (
        <div className="db-optin">
          <label htmlFor="lb-nickname">Leaderboard name</label>
          <input
            id="lb-nickname" type="text" value={nickname} maxLength={NICKNAME_MAX}
            onChange={e => setNickname(e.target.value)} placeholder="Nickname (optional)" autoComplete="off"
          />
          {settings.optIn ? (
            <>
              <button type="button" className="db-btn" disabled={saving} onClick={() => saveSettings(true)}>Save name</button>
              <button type="button" className="db-btn db-btn-quiet" disabled={saving} onClick={() => saveSettings(false)}>Hide me</button>
            </>
          ) : (
            <button type="button" className="db-btn db-btn-gold" disabled={saving} onClick={() => saveSettings(true)}>Join the leaderboard</button>
          )}
          <p className="db-muted">
            {settings.optIn
              ? "Other students see this name (or your first name and initial), your points and paper count."
              : "You are hidden. Only you can see your own row until you join."}
          </p>
          {note ? <p className="db-muted" role="status">{note}</p> : null}
        </div>
      ) : null}

      {status === "loading" ? <p className="db-muted">Loading the leaderboard…</p> : null}
      {status === "error" ? <p className="db-alert" role="alert">The leaderboard could not be loaded. Please try again.</p> : null}
      {status === "ready" && rows.length === 0 ? (
        <p className="db-empty">
          Nobody has completed a {subject.name} paper {period === "week" ? "this week" : "yet"}. Tick one off to take first place.
        </p>
      ) : null}

      {status === "ready" && rows.length > 0 ? (
        <ol className="db-lb">
          {rows.map(row => (
            <li key={`${row.rank}-${row.displayName}`} data-me={row.isMe || undefined}>
              <span className="db-rank">{row.rank}</span>
              <span className="db-lb-name">
                {row.isMe ? "You" : row.displayName}
                <small>
                  {row.papers} {row.papers === 1 ? "paper" : "papers"}
                  {row.averagePercentage !== null ? ` · ${row.averagePercentage}% average` : ""}
                </small>
              </span>
              <span className="db-lb-track" aria-hidden><i style={{ width: `${Math.max(4, Math.round((row.points / rows[0].points) * 100))}%` }} /></span>
              <b>{row.points} pts</b>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  )
}
