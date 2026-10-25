"use client"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import {
  COLORS, Panel, PeriodNote, RankList, SectionState, Stat, axisTick, num, panelGrid, shortDay, statGrid,
  tooltipStyle, useSection, type PanelProps,
} from "./ui"

interface ToolStats {
  generated: number; failed: number; partial: number
  avg_ms: number | null; p50_ms: number | null; p90_ms: number | null
  requested: number; supplied: number; history_failed: number; limit_hits: number
  fail_reasons: { reason: string; count: number }[]
  subjects: { subject: string; count: number }[]
}
interface ToolsData {
  tools: { worksheet?: ToolStats; test?: ToolStats } | null
  sign_in: { completed: number; new_accounts: number; failed: number; fail_reasons: { reason: string; count: number }[] }
  daily: { day: string; worksheets: number; tests: number; failures: number; sign_in_failures: number }[]
}

const REASONS: Record<string, string> = {
  no_questions: "No questions matched the filters",
  query_error: "Database query failed",
  save_error: "Could not save the worksheet",
  server_error: "Unexpected server error",
  no_pdfs: "No PDFs for the chosen questions",
  download_failed: "Question PDFs could not be downloaded",
}

const seconds = (ms: number | null) => (ms == null ? "—" : `${(ms / 1000).toFixed(1)}s`)
const rate = (part: number, whole: number) => (whole ? `${Math.round((part / whole) * 1000) / 10}%` : "—")

function ToolBlock({ title, stats, color }: { title: string; stats: ToolStats | undefined; color: string }) {
  if (!stats) return null
  const attempts = stats.generated + stats.failed
  return (
    <>
      <h3 style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gm-text)", margin: "0.5rem 0 0.75rem" }}>{title}</h3>
      <div style={statGrid}>
        <Stat title="PDFs made" value={num(stats.generated)} note={`${num(stats.partial)} partial`} color={color} />
        <Stat title="Failure rate" value={rate(stats.failed, attempts)} note={`${num(stats.failed)} of ${num(attempts)} requests`}
          color={stats.failed / Math.max(attempts, 1) > 0.05 ? COLORS.pink : "var(--gm-text)"} />
        <Stat title="Time to build" value={seconds(stats.p50_ms)} note={`typical · slowest 10% over ${seconds(stats.p90_ms)}`} color={COLORS.blue} />
        <Stat title="Questions supplied" value={rate(stats.supplied, stats.requested)} note={`${num(stats.supplied)} of ${num(stats.requested)} requested`} color={COLORS.green} />
        <Stat title="Question limit hit" value={num(stats.limit_hits)} note="students asking for more than 30" color={COLORS.amber} />
        {title.startsWith("Worksheet") && (
          <Stat title="History not saved" value={num(stats.history_failed)} note="PDF still delivered" color={stats.history_failed ? COLORS.pink : "var(--gm-text)"} />
        )}
      </div>
      <div style={panelGrid}>
        <Panel title="Why requests failed">
          <RankList rows={stats.fail_reasons.map(r => ({ name: REASONS[r.reason] ?? r.reason, value: r.count, color: COLORS.pink }))} />
        </Panel>
        <Panel title="Most requested subjects">
          <RankList rows={stats.subjects.map(s => ({ name: s.subject, value: s.count, color }))} />
        </Panel>
      </div>
    </>
  )
}

export default function ToolsPanel({ query }: PanelProps) {
  const { data, error, loading } = useSection<ToolsData & { first_day?: string; last_day?: string; partial?: boolean }>("tools", query, 120_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const s = data.sign_in
  const chart = data.daily.map(d => ({ ...d, label: shortDay(d.day) }))

  return (
    <div>
      <PeriodNote firstDay={data.first_day} lastDay={data.last_day} partial={data.partial}
        extra="recorded by the server, so ad blockers do not hide these" />
      <Panel title="Generated PDFs and failures per day" style={{ marginBottom: "1.5rem" }}>
        <div style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={axisTick} minTickGap={16} />
              <YAxis allowDecimals={false} tick={axisTick} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              <Bar dataKey="worksheets" name="Worksheets" stackId="ok" fill={COLORS.purple} />
              <Bar dataKey="tests" name="Tests" stackId="ok" fill={COLORS.cyan} />
              <Bar dataKey="failures" name="Failed" fill={COLORS.pink} />
              <Bar dataKey="sign_in_failures" name="Sign-in failures" fill={COLORS.amber} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <ToolBlock title="Worksheet Generator" stats={data.tools?.worksheet} color={COLORS.purple} />
      <ToolBlock title="Test Builder" stats={data.tools?.test} color={COLORS.cyan} />

      <h3 style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gm-text)", margin: "0.5rem 0 0.75rem" }}>Signing in</h3>
      <div style={statGrid}>
        <Stat title="Sign-ins" value={num(s.completed)} note={`${num(s.new_accounts)} new accounts`} color={COLORS.green} />
        <Stat title="Failed sign-ins" value={num(s.failed)} note={`${rate(s.failed, s.completed + s.failed)} of attempts that reached the server`}
          color={s.failed ? COLORS.pink : "var(--gm-text)"} />
      </div>
      {s.fail_reasons.length > 0 && (
        <Panel title="Sign-in failure reasons" note="Supabase error codes, for example bad_code_verifier when the login started on another device or browser tab.">
          <RankList rows={s.fail_reasons.map(r => ({ name: r.reason, value: r.count, color: COLORS.amber }))} />
        </Panel>
      )}
    </div>
  )
}
