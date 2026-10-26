"use client"
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import {
  COLORS, Panel, PeriodNote, RankList, SectionState, Stat, axisTick, change, countryName, formatSeconds, num,
  panelGrid, pct, shortDay, statGrid, tooltipStyle, useSection, type PanelProps,
} from "./ui"

interface Totals {
  visitors: number; new_visitors: number; views: number
  signed_in_visitors?: number; sessions?: number; bounce_rate?: number | null; pages_per_session?: number | null
  avg_session_seconds?: number | null; avg_engaged_seconds?: number | null; unknown_country?: number
}
interface OverviewData {
  days: number
  first_day?: string
  last_day?: string
  partial?: boolean
  totals: Totals & { live: number; today: number; yesterday: number; last7: number; signups: number }
  previous?: Totals
  daily: { day: string; views: number; visitors: number; new_visitors: number; signed_in: number; signups: number; sessions?: number }[]
  pages: { path: string; views: number; visitors: number }[]
  referrers: { host: string; visitors: number }[]
  countries: { country: string; visitors: number }[]
  devices: { device: string; visitors: number }[]
}

export default function OverviewPanel({ query }: PanelProps) {
  const { data, error, loading } = useSection<OverviewData>("overview", query, 60_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const t = data.totals
  const p = data.previous
  const chart = data.daily.map(d => ({ ...d, label: shortDay(d.day) }))
  // Average over finished days only: today's partial count would drag it down.
  const fullDays = data.partial ? data.daily.slice(0, -1) : data.daily
  const avgDaily = fullDays.length ? Math.round(fullDays.reduce((s, d) => s + d.visitors, 0) / fullDays.length) : 0
  const unknownShare = t.visitors && t.unknown_country != null ? Math.round((t.unknown_country / t.visitors) * 100) : null

  return (
    <div>
      <PeriodNote
        firstDay={data.first_day} lastDay={data.last_day} partial={data.partial}
        extra={unknownShare != null ? `country unknown for ${unknownShare}% of visitors` : undefined}
      />
      <div style={statGrid}>
        <Stat title="Online now" value={num(t.live)} note="last 30 minutes" color={COLORS.green} />
        <Stat title="Today" value={num(t.today)} note={`yesterday ${num(t.yesterday)}`} color="var(--gm-blue)" />
        <Stat title="Visitors" value={num(t.visitors)} delta={change(t.visitors, p?.visitors)}
          note={`${num(t.new_visitors)} new · avg ${num(avgDaily)}/day`} color={COLORS.purple} />
        <Stat title="Signed-in visitors" value={num(t.signed_in_visitors ?? null)} delta={change(t.signed_in_visitors, p?.signed_in_visitors)}
          note="browsers with a GradeMax session" color={COLORS.green} />
        <Stat title="Visits" value={num(t.sessions ?? null)} delta={change(t.sessions, p?.sessions)}
          note={t.pages_per_session ? `${t.pages_per_session} pages per visit` : "sessions"} color={COLORS.cyan} />
        <Stat title="Avg visit length" value={formatSeconds(t.avg_session_seconds)} delta={change(t.avg_session_seconds, p?.avg_session_seconds)}
          note={`reading time per page ${formatSeconds(t.avg_engaged_seconds)}`} color={COLORS.blue} />
        <Stat title="Bounce rate" value={pct(t.bounce_rate)} delta={change(t.bounce_rate, p?.bounce_rate)} lowerIsBetter
          note="left after one page, under 10s" color={COLORS.pink} />
        <Stat title="Page views" value={num(t.views)} delta={change(t.views, p?.views)}
          note={t.visitors ? `${(t.views / t.visitors).toFixed(1)} per visitor` : undefined} color={COLORS.cyan} />
        <Stat title="New accounts" value={num(t.signups)} note="all countries" color={COLORS.amber} />
      </div>

      <Panel title="Visitors per day" style={{ marginBottom: "1.5rem" }}>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chart} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={axisTick} minTickGap={16} />
              <YAxis allowDecimals={false} tick={axisTick} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              <Area type="monotone" dataKey="views" name="Page views" stroke={COLORS.cyan} fill={COLORS.cyan} fillOpacity={0.12} />
              <Area type="monotone" dataKey="sessions" name="Visits" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.1} />
              <Area type="monotone" dataKey="visitors" name="Visitors" stroke={COLORS.blue} fill={COLORS.blue} fillOpacity={0.25} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <Panel title="New visitors, signed-in visitors and new accounts" style={{ marginBottom: "1.5rem" }}>
        <div style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={axisTick} minTickGap={16} />
              <YAxis allowDecimals={false} tick={axisTick} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              <Bar dataKey="new_visitors" name="New visitors" fill={COLORS.purple} radius={[3, 3, 0, 0]} />
              <Bar dataKey="signed_in" name="Signed-in visitors" fill={COLORS.green} radius={[3, 3, 0, 0]} />
              <Bar dataKey="signups" name="New accounts" fill={COLORS.amber} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div style={panelGrid}>
        <Panel title="Top pages">
          <RankList rows={data.pages.map(pg => ({ name: pg.path, value: pg.views, sub: `· ${num(pg.visitors)} visitors` }))} />
        </Panel>
        <Panel title="Where visitors come from">
          <RankList rows={data.referrers.map(r => ({ name: r.host, value: r.visitors }))} />
        </Panel>
        <Panel title="Countries">
          <RankList rows={data.countries.map(c => ({ name: countryName(c.country), value: c.visitors }))} />
        </Panel>
        <Panel title="Devices">
          <RankList rows={data.devices.map(d => ({ name: d.device.charAt(0).toUpperCase() + d.device.slice(1), value: d.visitors }))} />
        </Panel>
      </div>
    </div>
  )
}
