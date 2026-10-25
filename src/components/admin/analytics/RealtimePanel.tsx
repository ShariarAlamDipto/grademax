"use client"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import {
  CHANNEL_LABELS, COLORS, DataTable, Empty, Panel, RankList, SectionState, Stat, axisTick, countryName, num,
  panelGrid, statGrid, tooltipStyle, useSection,
} from "./ui"

interface RealtimeData {
  active_5m: number
  active_30m: number
  per_minute: { minute: number; views: number }[]
  pages_now: { path: string; visitors: number }[]
  recent: { at: string; path: string; country: string | null; device: string; channel: string | null; referrer: string | null; new: boolean }[]
  events: { at: string; name: string; label: string | null }[]
}

const EVENT_LABELS: Record<string, string> = {
  download: "Downloaded", outbound: "Left for", sign_in: "Signed in", sign_up: "New account",
  order_placed: "Order placed", worksheet_generated: "Worksheet generated", test_generated: "Test generated",
}

const time = (iso: string) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })

export default function RealtimePanel() {
  const { data, error, loading } = useSection<RealtimeData>("realtime", 30, 15_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const views30 = data.per_minute.reduce((s, m) => s + m.views, 0)
  const chart = data.per_minute.map(m => ({ label: m.minute === 0 ? "now" : `-${m.minute}m`, views: m.views }))

  return (
    <div>
      <p style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginBottom: "1rem" }}>Updates every 15 seconds.</p>
      <div style={statGrid}>
        <Stat title="Active now" value={num(data.active_5m)} note="visitors in the last 5 minutes" color={COLORS.green} />
        <Stat title="Last 30 minutes" value={num(data.active_30m)} note="visitors" color="var(--gm-blue)" />
        <Stat title="Page views" value={num(views30)} note="last 30 minutes" color={COLORS.cyan} />
      </div>

      <Panel title="Page views per minute" style={{ marginBottom: "1.5rem" }}>
        <div style={{ height: 160 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ left: -20, right: 8, top: 8, bottom: 0 }}>
              <XAxis dataKey="label" tick={axisTick} interval={4} />
              <YAxis allowDecimals={false} tick={axisTick} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="views" name="Page views" fill={COLORS.green} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div style={panelGrid}>
        <Panel title="Being read right now">
          <RankList rows={data.pages_now.map(p => ({ name: p.path, value: p.visitors, color: COLORS.green }))} />
        </Panel>
        <Panel title="Latest actions">
          {data.events.length === 0 ? <Empty>No downloads, sign-ins or orders in the last 30 minutes.</Empty> : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem", fontSize: "0.8rem" }}>
              {data.events.map((e, i) => (
                <div key={i} style={{ display: "flex", gap: "0.6rem" }}>
                  <span style={{ color: "var(--gm-text-3)", flexShrink: 0 }}>{time(e.at)}</span>
                  <span style={{ color: "var(--gm-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {EVENT_LABELS[e.name] ?? e.name}{e.label ? ` · ${e.label}` : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Live feed of page views">
        <DataTable
          rows={data.recent}
          columns={[
            { key: "at", title: "Time", render: r => time(r.at) },
            { key: "path", title: "Page", render: r => r.path },
            { key: "who", title: "Visitor", render: r => (r.new ? "New" : "Returning") },
            { key: "from", title: "Came from", render: r => (r.channel ? CHANNEL_LABELS[r.channel] ?? r.channel : r.referrer ?? "—") },
            { key: "country", title: "Country", render: r => countryName(r.country ?? "??") },
            { key: "device", title: "Device", render: r => r.device },
          ]}
        />
      </Panel>
    </div>
  )
}
