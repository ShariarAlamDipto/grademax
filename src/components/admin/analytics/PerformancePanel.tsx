"use client"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import {
  COLORS, DataTable, Empty, Panel, PeriodNote, SectionState, Stat, axisTick, countryName, num, panelGrid,
  shortDay, statGrid, tooltipStyle, useSection, type PanelProps,
} from "./ui"

interface Summary { samples: number; p50: number | null; p75: number | null; p95: number | null; good: number | null; poor: number | null }
interface PerformanceData {
  first_day: string; last_day: string; partial: boolean
  metrics: Record<"LCP" | "INP" | "CLS" | "FCP" | "TTFB", Summary>
  by_device: { device: string; samples: number; lcp_p75: number | null; inp_p75: number | null; cls_p75: number | null }[]
  by_country: { country: string; samples: number; lcp_p75: number | null; ttfb_p75: number | null }[]
  slow_pages: { path: string; samples: number; lcp_p75: number | null; inp_p75: number | null; cls_p75: number | null }[]
  daily: { day: string; lcp_p75: number | null; inp_p75: number | null; samples: number }[]
  errors: { total: number; visitors: number; top: { label: string; count: number; visitors: number; last_path: string }[] }
}

// Google's thresholds: [good at or under, poor above]. CLS is stored x1000.
const METRICS = [
  { key: "LCP", title: "Largest paint (LCP)", limits: [2500, 4000], note: "main content visible" },
  { key: "INP", title: "Responsiveness (INP)", limits: [200, 500], note: "delay after a tap or click" },
  { key: "CLS", title: "Layout shift (CLS)", limits: [100, 250], note: "content jumping around" },
  { key: "FCP", title: "First paint (FCP)", limits: [1800, 3000], note: "anything visible" },
  { key: "TTFB", title: "Server response (TTFB)", limits: [800, 1800], note: "first byte from the server" },
] as const

const fmt = (key: string, v: number | null) =>
  v == null ? "—" : key === "CLS" ? (v / 1000).toFixed(2) : v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${Math.round(v)}ms`
const grade = (v: number | null, [good, poor]: readonly number[]) =>
  v == null ? "var(--gm-text)" : v <= good ? COLORS.green : v > poor ? COLORS.pink : COLORS.amber

export default function PerformancePanel({ query }: PanelProps) {
  const { data, error, loading } = useSection<PerformanceData>("performance", query, 300_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const chart = data.daily.map(d => ({ ...d, label: shortDay(d.day) }))
  const limitsOf = (key: string) => METRICS.find(m => m.key === key)!.limits

  return (
    <div>
      <PeriodNote firstDay={data.first_day} lastDay={data.last_day} partial={data.partial}
        extra="real visitors' browsers, measured on the page each visit landed on; p75 = 3 in 4 visits were at least this fast" />
      <div style={statGrid}>
        {METRICS.map(m => {
          const s = data.metrics[m.key]
          return (
            <Stat key={m.key} title={m.title} value={fmt(m.key, s.p75)} color={grade(s.p75, m.limits)}
              note={s.samples ? `${m.note} · ${s.good ?? 0}% good, ${s.poor ?? 0}% poor · p95 ${fmt(m.key, s.p95)} · ${num(s.samples)} visits` : `${m.note} · no data yet`} />
          )
        })}
        <Stat title="JavaScript errors" value={num(data.errors.total)} note={`seen by ${num(data.errors.visitors)} visitors`}
          color={data.errors.total ? COLORS.pink : "var(--gm-text)"} />
      </div>

      <Panel title="Daily p75" note="Green under 2.5s (LCP) and 200ms (INP) is good." style={{ marginBottom: "1.5rem" }}>
        <div style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chart} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gm-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={axisTick} minTickGap={16} />
              <YAxis yAxisId="lcp" tick={axisTick} />
              <YAxis yAxisId="inp" orientation="right" tick={axisTick} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              <Line yAxisId="lcp" type="monotone" dataKey="lcp_p75" name="LCP p75 (ms)" stroke={COLORS.blue} strokeWidth={2} dot={false} connectNulls />
              <Line yAxisId="inp" type="monotone" dataKey="inp_p75" name="INP p75 (ms)" stroke={COLORS.purple} strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div style={panelGrid}>
        <Panel title="By device">
          <DataTable rows={data.by_device} columns={[
            { key: "device", title: "Device", render: r => r.device },
            { key: "lcp", title: "LCP p75", align: "right", render: r => <span style={{ color: grade(r.lcp_p75, limitsOf("LCP")) }}>{fmt("LCP", r.lcp_p75)}</span> },
            { key: "inp", title: "INP p75", align: "right", render: r => <span style={{ color: grade(r.inp_p75, limitsOf("INP")) }}>{fmt("INP", r.inp_p75)}</span> },
            { key: "cls", title: "CLS p75", align: "right", render: r => <span style={{ color: grade(r.cls_p75, limitsOf("CLS")) }}>{fmt("CLS", r.cls_p75)}</span> },
            { key: "n", title: "Visits", align: "right", render: r => num(r.samples) },
          ]} />
        </Panel>
        <Panel title="By country">
          <DataTable rows={data.by_country} columns={[
            { key: "country", title: "Country", render: r => countryName(r.country) },
            { key: "lcp", title: "LCP p75", align: "right", render: r => <span style={{ color: grade(r.lcp_p75, limitsOf("LCP")) }}>{fmt("LCP", r.lcp_p75)}</span> },
            { key: "ttfb", title: "TTFB p75", align: "right", render: r => <span style={{ color: grade(r.ttfb_p75, limitsOf("TTFB")) }}>{fmt("TTFB", r.ttfb_p75)}</span> },
            { key: "n", title: "Visits", align: "right", render: r => num(r.samples) },
          ]} />
        </Panel>
      </div>

      <Panel title="Slowest pages" note="Landing pages with at least 5 measured visits, slowest LCP first." style={{ marginBottom: "1.5rem" }}>
        <DataTable rows={data.slow_pages} exportName="slow-pages" columns={[
          { key: "path", title: "Page", render: r => r.path, csv: r => r.path },
          { key: "lcp", title: "LCP p75", align: "right", render: r => <span style={{ color: grade(r.lcp_p75, limitsOf("LCP")) }}>{fmt("LCP", r.lcp_p75)}</span>, sort: r => r.lcp_p75 ?? -1 },
          { key: "inp", title: "INP p75", align: "right", render: r => fmt("INP", r.inp_p75), sort: r => r.inp_p75 ?? -1 },
          { key: "cls", title: "CLS p75", align: "right", render: r => fmt("CLS", r.cls_p75), sort: r => r.cls_p75 ?? -1 },
          { key: "n", title: "Visits", align: "right", render: r => num(r.samples), sort: r => r.samples },
        ]} />
      </Panel>

      <Panel title="Most common JavaScript errors" note="Ad scripts, browser extensions and known harmless warnings are left out.">
        {data.errors.top.length === 0 ? <Empty>No errors recorded. </Empty> : (
          <DataTable rows={data.errors.top} exportName="js-errors" columns={[
            { key: "label", title: "Error", render: r => <span title={r.label}>{r.label}</span>, csv: r => r.label },
            { key: "count", title: "Times", align: "right", render: r => num(r.count), sort: r => r.count },
            { key: "visitors", title: "Visitors", align: "right", render: r => num(r.visitors), sort: r => r.visitors },
            { key: "page", title: "Last seen on", render: r => r.last_path, csv: r => r.last_path },
          ]} />
        )}
      </Panel>
    </div>
  )
}
