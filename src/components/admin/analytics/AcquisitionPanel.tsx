"use client"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import {
  CHANNEL_COLORS, CHANNEL_LABELS, COLORS, DataTable, Empty, Panel, RankList, SectionState, Stat, axisTick,
  countryName, formatSeconds, num, panelGrid, pct, shortDay, statGrid, tooltipStyle, useSection,
} from "./ui"

interface ChannelRow { channel: string; sessions: number; visitors: number; bounce_rate: number | null; pages_per_session: number | null; avg_seconds: number | null }
interface AcquisitionData {
  channels: ChannelRow[]
  daily: ({ day: string } & Record<string, number | string>)[]
  referrers: { host: string; sessions: number; channel: string | null }[]
  campaigns: { source: string | null; medium: string | null; campaign: string | null; sessions: number }[]
  landing: { path: string; channel: string; sessions: number }[]
  new_vs_returning: { new: number; returning: number }
  countries: { country: string; sessions: number; visitors: number }[]
}

const DAILY_SERIES = ["search", "direct", "social", "ai", "referral", "campaigns"] as const

export default function AcquisitionPanel({ days }: { days: number }) {
  const { data, error, loading } = useSection<AcquisitionData>("acquisition", days, 120_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const total = data.channels.reduce((s, c) => s + c.sessions, 0)
  const share = (ch: string) => {
    const n = data.channels.find(c => c.channel === ch)?.sessions ?? 0
    return total ? `${Math.round((n / total) * 100)}%` : "—"
  }
  const nvr = data.new_vs_returning
  const chart = data.daily.map(d => ({ ...d, label: shortDay(String(d.day)) }))

  return (
    <div>
      <div style={statGrid}>
        <Stat title="Visits" value={num(total)} note={`${num(nvr.new)} new · ${num(nvr.returning)} returning visitors`} color={COLORS.cyan} />
        <Stat title="From search" value={share("search")} note="Google, Bing and others" color={COLORS.blue} />
        <Stat title="From AI assistants" value={share("ai")} note="ChatGPT, Gemini, Perplexity…" color={COLORS.purple} />
        <Stat title="From social" value={share("social")} note="Facebook, YouTube, Discord…" color={COLORS.pink} />
      </div>

      <Panel title="Visits per day by channel" style={{ marginBottom: "1.5rem" }}>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chart} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={axisTick} minTickGap={16} />
              <YAxis allowDecimals={false} tick={axisTick} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              {DAILY_SERIES.map(key => (
                <Area key={key} type="monotone" stackId="1" dataKey={key} name={CHANNEL_LABELS[key]}
                  stroke={CHANNEL_COLORS[key]} fill={CHANNEL_COLORS[key]} fillOpacity={0.35} />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <Panel title="Channels" note="How visitors from each source behave once they arrive." style={{ marginBottom: "1.5rem" }}>
        <DataTable<ChannelRow>
          rows={data.channels}
          initialSort="sessions"
          columns={[
            { key: "channel", title: "Channel", render: r => (
              <span style={{ display: "inline-flex", alignItems: "center", gap: "0.45rem" }}>
                <span style={{ width: 8, height: 8, borderRadius: 99, background: CHANNEL_COLORS[r.channel] ?? COLORS.slate }} />
                {CHANNEL_LABELS[r.channel] ?? r.channel}
              </span>
            ), sort: r => r.channel },
            { key: "sessions", title: "Visits", align: "right", render: r => num(r.sessions), sort: r => r.sessions },
            { key: "visitors", title: "Visitors", align: "right", render: r => num(r.visitors), sort: r => r.visitors },
            { key: "pps", title: "Pages / visit", align: "right", render: r => r.pages_per_session ?? "—", sort: r => r.pages_per_session ?? -1 },
            { key: "time", title: "Visit length", align: "right", render: r => formatSeconds(r.avg_seconds), sort: r => r.avg_seconds ?? -1 },
            { key: "bounce", title: "Bounce", align: "right", render: r => pct(r.bounce_rate), sort: r => r.bounce_rate ?? -1 },
          ]}
        />
      </Panel>

      <div style={panelGrid}>
        <Panel title="Referring websites">
          <RankList rows={data.referrers.map(r => ({ name: r.host, value: r.sessions, color: CHANNEL_COLORS[r.channel ?? ""] }))} />
        </Panel>
        <Panel title="Landing pages by channel">
          <RankList rows={data.landing.map(l => ({ name: `${l.path} · ${CHANNEL_LABELS[l.channel] ?? l.channel}`, value: l.sessions, color: CHANNEL_COLORS[l.channel] }))} />
        </Panel>
        <Panel title="Countries">
          <RankList rows={data.countries.map(c => ({ name: countryName(c.country), value: c.sessions, sub: `· ${num(c.visitors)} visitors` }))} />
        </Panel>
        <Panel title="Campaigns (utm tags)" note="Add ?utm_source=facebook&utm_campaign=eid to links you share to see them here.">
          {data.campaigns.length === 0 ? <Empty>No tagged links used yet.</Empty> : (
            <RankList rows={data.campaigns.map(c => ({
              name: [c.source, c.medium, c.campaign].filter(Boolean).join(" / "), value: c.sessions, color: COLORS.amber,
            }))} />
          )}
        </Panel>
      </div>
    </div>
  )
}
