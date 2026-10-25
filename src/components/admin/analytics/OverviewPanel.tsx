"use client"
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import {
  COLORS, Panel, RankList, SectionState, Stat, axisTick, countryName, formatSeconds, num, panelGrid, pct,
  shortDay, statGrid, tooltipStyle, useSection,
} from "./ui"

interface OverviewData {
  days: number
  totals: {
    live: number; today: number; yesterday: number; last7: number
    visitors: number; new_visitors: number; views: number; signups: number
    sessions?: number; bounce_rate?: number | null; pages_per_session?: number | null
    avg_session_seconds?: number | null; avg_engaged_seconds?: number | null
  }
  daily: { day: string; views: number; visitors: number; new_visitors: number; signed_in: number; signups: number; sessions?: number }[]
  pages: { path: string; views: number; visitors: number }[]
  referrers: { host: string; visitors: number }[]
  countries: { country: string; visitors: number }[]
  devices: { device: string; visitors: number }[]
}

export default function OverviewPanel({ days }: { days: number }) {
  const { data, error, loading } = useSection<OverviewData>("overview", days, 60_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const t = data.totals
  const chart = data.daily.map(d => ({ ...d, label: shortDay(d.day) }))
  const avgDaily = data.daily.length ? Math.round(data.daily.reduce((s, d) => s + d.visitors, 0) / data.daily.length) : 0

  return (
    <div>
      <div style={statGrid}>
        <Stat title="Online now" value={num(t.live)} note="last 30 minutes" color={COLORS.green} />
        <Stat title="Today" value={num(t.today)} note={`yesterday ${num(t.yesterday)}`} color="var(--gm-blue)" />
        <Stat title="Last 7 days" value={num(t.last7)} note="unique visitors" color="var(--gm-text)" />
        <Stat title={`${data.days}-day visitors`} value={num(t.visitors)} note={`${num(t.new_visitors)} new · avg ${num(avgDaily)}/day`} color={COLORS.purple} />
        <Stat title="Visits" value={num(t.sessions ?? null)} note={t.pages_per_session ? `${t.pages_per_session} pages per visit` : "sessions"} color={COLORS.cyan} />
        <Stat title="Avg visit length" value={formatSeconds(t.avg_session_seconds)} note={`reading time per page ${formatSeconds(t.avg_engaged_seconds)}`} color={COLORS.blue} />
        <Stat title="Bounce rate" value={pct(t.bounce_rate)} note="left after one page, under 10s" color={COLORS.pink} />
        <Stat title="Page views" value={num(t.views)} note={t.visitors ? `${(t.views / t.visitors).toFixed(1)} per visitor` : undefined} color={COLORS.cyan} />
        <Stat title="New accounts" value={num(t.signups)} note={`in ${data.days} days`} color={COLORS.amber} />
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
          <RankList rows={data.pages.map(p => ({ name: p.path, value: p.views, sub: `· ${num(p.visitors)} visitors` }))} />
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
