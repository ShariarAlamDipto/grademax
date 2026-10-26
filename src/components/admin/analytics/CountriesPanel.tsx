"use client"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import {
  COLORS, DataTable, Panel, PeriodNote, SectionState, Stat, axisTick, countryName, formatSeconds, num, pct,
  shortDay, smallButton, statGrid, tooltipStyle, useSection, type PanelProps,
} from "./ui"

interface CountryRow {
  country: string; visitors: number; views: number; share: number | null; avg_engaged: number | null
  sessions: number; bounce_rate: number | null; engagement_rate?: number | null; downloads: number; sign_ins: number; sign_ups: number
  orders: number; generations: number; prev_visitors: number; change: number | null
  top_pages: { path: string; views: number }[]
}
interface CountriesData {
  first_day: string; last_day: string; partial: boolean
  total_visitors: number; unknown_visitors: number
  countries: CountryRow[]
  trend: { day: string; visitors: Record<string, number> }[]
}

const LINE_COLORS = [COLORS.blue, COLORS.green, COLORS.amber, COLORS.purple, COLORS.pink]

export default function CountriesPanel({ query, onPickCountry }: PanelProps) {
  const { data, error, loading } = useSection<CountriesData>("countries", query, 120_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const known = data.countries.filter(c => c.country !== "??")
  const top = known[0]
  const unknownShare = data.total_visitors ? Math.round((data.unknown_visitors / data.total_visitors) * 1000) / 10 : 0
  const trendKeys = data.trend[0] ? Object.keys(data.trend[0].visitors) : []
  const chart = data.trend.map(t => ({ label: shortDay(t.day), ...t.visitors }))

  return (
    <div>
      <PeriodNote firstDay={data.first_day} lastDay={data.last_day} partial={data.partial}
        extra="the country filter above applies to every other section" />
      <div style={statGrid}>
        <Stat title="Countries" value={num(known.length)} note="with at least one visitor" color={COLORS.blue} />
        <Stat title="Top country" value={top ? countryName(top.country) : "—"} note={top ? `${pct(top.share)} of visitors` : undefined} color={COLORS.green} />
        <Stat title="Country unknown" value={`${unknownShare}%`} note={`${num(data.unknown_visitors)} visitors. Above ~5% means Cloudflare's country header is missing.`}
          color={unknownShare > 5 ? COLORS.pink : "var(--gm-text)"} />
      </div>

      {trendKeys.length > 0 && (
        <Panel title="Visitors per day, top countries" style={{ marginBottom: "1.5rem" }}>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={axisTick} minTickGap={16} />
                <YAxis allowDecimals={false} tick={axisTick} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
                {trendKeys.map((cc, i) => (
                  <Line key={cc} type="monotone" dataKey={cc} name={countryName(cc)} stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      )}

      <Panel title="All countries" note="Conversions come from server-recorded events. Change compares visitors with the previous period of the same length. Engaged under 50% (in pink, with 10+ visits) usually means automated traffic.">
        <DataTable<CountryRow>
          rows={data.countries}
          initialSort="visitors"
          exportName="countries"
          searchText={r => `${countryName(r.country)} ${r.country}`}
          columns={[
            { key: "country", title: "Country", render: r => countryName(r.country), sort: r => countryName(r.country), csv: r => countryName(r.country) },
            { key: "code", title: "Code", render: r => r.country, csv: r => r.country },
            { key: "visitors", title: "Visitors", align: "right", render: r => num(r.visitors), sort: r => r.visitors },
            { key: "share", title: "Share", align: "right", render: r => pct(r.share), sort: r => r.share ?? 0 },
            { key: "change", title: "Change", align: "right", sort: r => r.change ?? -1e9, csv: r => r.change,
              render: r => r.change == null ? <span style={{ color: "var(--gm-text-3)" }}>new</span>
                : <span style={{ color: r.change >= 0 ? COLORS.green : COLORS.pink }}>{r.change > 0 ? "+" : ""}{r.change}%</span> },
            { key: "sessions", title: "Visits", align: "right", render: r => num(r.sessions), sort: r => r.sessions },
            { key: "views", title: "Page views", align: "right", render: r => num(r.views), sort: r => r.views },
            { key: "engaged", title: "Reading time", align: "right", render: r => formatSeconds(r.avg_engaged), sort: r => r.avg_engaged ?? -1 },
            { key: "bounce", title: "Bounce", align: "right", render: r => pct(r.bounce_rate), sort: r => r.bounce_rate ?? -1 },
            // Low engagement with many visits usually means automated traffic.
            { key: "engaged", title: "Engaged", align: "right", sort: r => r.engagement_rate ?? -1, csv: r => r.engagement_rate ?? null,
              render: r => <span style={{ color: r.engagement_rate != null && r.engagement_rate < 50 && r.sessions >= 10 ? COLORS.pink : undefined }}>{pct(r.engagement_rate)}</span> },
            { key: "downloads", title: "Downloads", align: "right", render: r => num(r.downloads), sort: r => r.downloads },
            { key: "signins", title: "Sign-ins", align: "right", render: r => num(r.sign_ins), sort: r => r.sign_ins },
            { key: "signups", title: "New accounts", align: "right", render: r => num(r.sign_ups), sort: r => r.sign_ups },
            { key: "gens", title: "Worksheets/tests", align: "right", render: r => num(r.generations), sort: r => r.generations },
            { key: "orders", title: "Orders", align: "right", render: r => num(r.orders), sort: r => r.orders },
            { key: "top", title: "Top page", render: r => r.top_pages[0]?.path ?? "—", csv: r => r.top_pages[0]?.path ?? "" },
            ...(onPickCountry ? [{
              key: "focus", title: "", render: (r: CountryRow) => (
                <button onClick={() => onPickCountry(r.country)} style={smallButton}>Focus</button>
              ),
            }] : []),
          ]}
        />
      </Panel>
    </div>
  )
}
