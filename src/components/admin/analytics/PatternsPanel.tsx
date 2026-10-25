"use client"
import { COLORS, DataTable, Panel, RankList, SectionState, formatSeconds, num, panelGrid, useSection } from "./ui"

interface PatternsData {
  heatmap: { dow: number; hour: number; views: number }[]
  browsers: { name: string; visitors: number }[]
  os: { name: string; visitors: number }[]
  devices: { name: string; visitors: number; avg_engaged: number | null; pages_per_visitor: number | null }[]
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const HOURS = Array.from({ length: 24 }, (_, h) => h)

function Heatmap({ cells }: { cells: PatternsData["heatmap"] }) {
  const lookup = new Map(cells.map(c => [`${c.dow}-${c.hour}`, c.views]))
  const max = Math.max(1, ...cells.map(c => c.views))
  const box = { width: "100%", aspectRatio: "1", borderRadius: "3px" }
  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ display: "grid", gridTemplateColumns: "2.5rem repeat(24, minmax(14px, 1fr))", gap: "3px", minWidth: "460px" }}>
        <span />
        {HOURS.map(h => (
          <span key={h} style={{ fontSize: "0.6rem", color: "var(--gm-text-3)", textAlign: "center" }}>{h % 3 === 0 ? h : ""}</span>
        ))}
        {DAYS.map((d, i) => (
          <div key={d} style={{ display: "contents" }}>
            <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", alignSelf: "center" }}>{d}</span>
            {HOURS.map(h => {
              const views = lookup.get(`${i + 1}-${h}`) ?? 0
              return (
                <div key={h} title={`${d} ${String(h).padStart(2, "0")}:00 · ${num(views)} page views`}
                  style={{ ...box, background: views ? `rgba(6, 182, 212, ${0.12 + (views / max) * 0.88})` : "var(--gm-border)" }} />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PatternsPanel({ days }: { days: number }) {
  const { data, error, loading } = useSection<PatternsData>("patterns", days, 300_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  return (
    <div>
      <Panel title="Busiest times" note="Page views by weekday and hour, Bangladesh time. Darker means busier." style={{ marginBottom: "1.5rem" }}>
        <Heatmap cells={data.heatmap} />
      </Panel>

      <Panel title="Devices" note="Compare how long people read on phones and on computers." style={{ marginBottom: "1.5rem" }}>
        <DataTable
          rows={data.devices}
          columns={[
            { key: "name", title: "Device", render: r => r.name.charAt(0).toUpperCase() + r.name.slice(1) },
            { key: "visitors", title: "Visitors", align: "right", render: r => num(r.visitors) },
            { key: "ppv", title: "Pages / visitor", align: "right", render: r => r.pages_per_visitor ?? "—" },
            { key: "time", title: "Reading time per page", align: "right", render: r => formatSeconds(r.avg_engaged) },
          ]}
        />
      </Panel>

      <div style={panelGrid}>
        <Panel title="Browsers">
          <RankList rows={data.browsers.map(b => ({ name: b.name, value: b.visitors, color: COLORS.cyan }))} />
        </Panel>
        <Panel title="Operating systems">
          <RankList rows={data.os.map(o => ({ name: o.name, value: o.visitors, color: COLORS.purple }))} />
        </Panel>
      </div>
    </div>
  )
}
