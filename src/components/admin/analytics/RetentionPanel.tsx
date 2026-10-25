"use client"
import { Empty, Panel, SectionState, num, useSection } from "./ui"

interface RetentionData { weeks: number; cohorts: { week: string; size: number; retained: number[] }[] }

const weekLabel = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })

export default function RetentionPanel() {
  const { data, error, loading } = useSection<RetentionData>("retention", 30, 600_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const cell = { padding: "0.45rem 0.5rem", textAlign: "center" as const, fontSize: "0.75rem", borderBottom: "1px solid var(--gm-border)", whiteSpace: "nowrap" as const }
  const offsets = Array.from({ length: data.weeks }, (_, i) => i)

  return (
    <Panel
      title="Weekly retention"
      note="Each row is the visitors first seen that week. Each cell is the share who came back in a later week. Week 0 is always 100%. Visitors are counted by an anonymous cookie, so a new device or a cleared browser looks like a new visitor."
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
                  <td style={{ ...cell, textAlign: "left", color: "var(--gm-text)" }}>Week of {weekLabel(c.week)}</td>
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
  )
}
