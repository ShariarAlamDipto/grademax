"use client"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import {
  COLORS, DataTable, Panel, RankList, SectionState, Stat, axisTick, formatSeconds, num, panelGrid, pct,
  statGrid, tooltipStyle, useSection,
} from "./ui"

interface PageRow {
  path: string; views: number; visitors: number; entries: number; exits: number
  exit_rate: number | null; bounce_rate: number | null; avg_engaged: number | null; avg_scroll: number | null
}
interface BehaviorData {
  sessions: { count: number; bounce_rate: number | null; pages_per_session: number | null; avg_seconds: number | null; median_seconds: number | null }
  session_lengths: { bucket: string; sessions: number }[]
  engagement: { bucket: string; views: number }[]
  pages: PageRow[]
  flows: { from: string; to: string; count: number }[]
  landing: { path: string; sessions: number; bounce_rate: number | null; avg_seconds: number | null }[]
  exits: { path: string; sessions: number }[]
  events: { name: string; count: number; visitors: number }[]
  downloads: { label: string; count: number; visitors: number }[]
  outbound: { label: string; count: number }[]
}

function MiniBars({ data, dataKey, name, color }: { data: object[]; dataKey: string; name: string; color: string }) {
  return (
    <div style={{ height: 180 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: -20, right: 8, top: 8, bottom: 0 }}>
          <XAxis dataKey="bucket" tick={axisTick} interval={0} />
          <YAxis allowDecimals={false} tick={axisTick} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey={dataKey} name={name} fill={color} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function BehaviorPanel({ days }: { days: number }) {
  const { data, error, loading } = useSection<BehaviorData>("behavior", days, 120_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const s = data.sessions
  const downloads = data.events.find(e => e.name === "download")

  return (
    <div>
      <div style={statGrid}>
        <Stat title="Visits" value={num(s.count)} note={`${s.pages_per_session ?? "—"} pages per visit`} color={COLORS.cyan} />
        <Stat title="Avg visit length" value={formatSeconds(s.avg_seconds)} note={`median ${formatSeconds(s.median_seconds)}`} color={COLORS.blue} />
        <Stat title="Bounce rate" value={pct(s.bounce_rate)} note="one page, under 10 seconds" color={COLORS.pink} />
        <Stat title="PDF downloads" value={num(downloads?.count ?? 0)} note={`by ${num(downloads?.visitors ?? 0)} visitors`} color={COLORS.green} />
      </div>

      <div style={panelGrid}>
        <Panel title="Pages per visit">
          <MiniBars data={data.session_lengths} dataKey="sessions" name="Visits" color={COLORS.purple} />
        </Panel>
        <Panel title="Reading time per page view" note="Active time: tab visible and the reader interacting.">
          <MiniBars data={data.engagement} dataKey="views" name="Page views" color={COLORS.blue} />
        </Panel>
      </div>

      <Panel title="Pages" note="Click a column to sort. Exit rate: share of views that ended the visit. Bounce rate: visits that started here and left after one page." style={{ marginBottom: "1.5rem" }}>
        <DataTable<PageRow>
          rows={data.pages}
          initialSort="views"
          columns={[
            { key: "path", title: "Page", render: r => <span title={r.path}>{r.path}</span>, sort: r => r.path },
            { key: "views", title: "Views", align: "right", render: r => num(r.views), sort: r => r.views },
            { key: "visitors", title: "Visitors", align: "right", render: r => num(r.visitors), sort: r => r.visitors },
            { key: "entries", title: "Entries", align: "right", render: r => num(r.entries), sort: r => r.entries },
            { key: "engaged", title: "Reading time", align: "right", render: r => formatSeconds(r.avg_engaged), sort: r => r.avg_engaged ?? -1 },
            { key: "scroll", title: "Scroll", align: "right", render: r => pct(r.avg_scroll), sort: r => r.avg_scroll ?? -1 },
            { key: "bounce", title: "Bounce", align: "right", render: r => pct(r.bounce_rate), sort: r => r.bounce_rate ?? -1 },
            { key: "exit", title: "Exit rate", align: "right", render: r => pct(r.exit_rate), sort: r => r.exit_rate ?? -1 },
          ]}
        />
      </Panel>

      <Panel title="Where people go next" note="The most common moves from one page to the next within a visit." style={{ marginBottom: "1.5rem" }}>
        <RankList rows={data.flows.map(f => ({ name: `${f.from}  →  ${f.to}`, value: f.count, color: COLORS.purple }))} />
      </Panel>

      <div style={panelGrid}>
        <Panel title="Landing pages" note="First page of each visit, with its bounce rate.">
          <RankList rows={data.landing.map(l => ({ name: l.path, value: l.sessions, sub: `· bounce ${pct(l.bounce_rate)}` }))} />
        </Panel>
        <Panel title="Exit pages" note="Last page of each visit.">
          <RankList rows={data.exits.map(e => ({ name: e.path, value: e.sessions, color: COLORS.pink }))} />
        </Panel>
        <Panel title="Most downloaded PDFs">
          <RankList rows={data.downloads.map(d => ({ name: d.label.split("/").slice(-3).join("/"), value: d.count, sub: `· ${num(d.visitors)} visitors`, color: COLORS.green }))} />
        </Panel>
        <Panel title="Links to other sites">
          <RankList rows={data.outbound.map(o => ({ name: o.label, value: o.count, color: COLORS.amber }))} />
        </Panel>
      </div>
    </div>
  )
}
