"use client"
import { COLORS, Empty, Panel, SectionState, Stat, num, statGrid, useSection, type PanelProps } from "./ui"

interface RetentionData {
  weeks: number
  day_n?: { days: number; visitors: number; returned: number; rate: number | null }[]
  cohorts: { week: string; size: number; complete?: boolean; retained: number[] }[]
}

const weekLabel = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })
const DAY_N_COLORS: Record<number, string> = { 1: COLORS.green, 7: COLORS.blue, 30: COLORS.purple }

export default function RetentionPanel({ query }: PanelProps) {
  const { data, error, loading } = useSection<RetentionData>("retention", query, 600_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const cell = { padding: "0.45rem 0.5rem", textAlign: "center" as const, fontSize: "0.75rem", borderBottom: "1px solid var(--gm-border)", whiteSpace: "nowrap" as const }
  const offsets = Array.from({ length: data.weeks }, (_, i) => i)

  return (
    <div>
      {data.day_n && (
        <div style={statGrid}>
          {data.day_n.map(d => (
            <Stat
              key={d.days}
              title={`D${d.days} return rate`}
              value={d.rate == null ? "—" : `${d.rate}%`}
              note={`${num(d.returned)} of ${num(d.visitors)} came back within ${d.days === 1 ? "a day" : `${d.days} days`}`}
              color={DAY_N_COLORS[d.days] ?? COLORS.blue}
            />
          ))}
        </div>
      )}
      <Panel
        title="Weekly retention"
        note="Each row is the visitors first seen that week; each cell is the share who came back in a later week. D-numbers only count visitors first seen long enough ago to have had the full window. Visitors are counted by an anonymous cookie, so a new device or a cleared browser looks like a new visitor."
      >
        {data.cohorts.length === 0 ? <Empty>No cohorts yet. The first row appears after a week of tracking.</Empty> : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ ...cell, textAlign: "left", color: "var(--gm-text-3)" }}>First seen</th>
                  <th style={{ ...cell, color: "var(--gm-text-3)" }}>Visitors</th>
                  {offsets.map(o => <th key={o} style={{ ...cell, color: "var(--gm-text-3)" }}>Week {o}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.cohorts.map(c => (
                  <tr key={c.week}>
                    <td style={{ ...cell, textAlign: "left", color: "var(--gm-text)" }}>
                      Week of {weekLabel(c.week)}
                      {c.complete === false && <span style={{ color: "var(--gm-text-3)", fontSize: "0.68rem" }}> · still filling</span>}
                    </td>
                    <td style={{ ...cell, color: "var(--gm-text-2)", fontWeight: 600 }}>{num(c.size)}</td>
                    {offsets.map(o => {
                      if (o >= c.retained.length) return <td key={o} style={cell} />
                      const share = c.size ? c.retained[o] / c.size : 0
                      return (
                        <td key={o} title={`${num(c.retained[o])} visitors`} style={{
                          ...cell,
                          background: `rgba(59, 130, 246, ${0.08 + share * 0.72})`,
                          color: share > 0.45 ? "#fff" : "var(--gm-text)",
                        }}>
                          {Math.round(share * 100)}%
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
