"use client"
import { COLORS, Empty, Panel, SectionState, num, panelGrid, useSection } from "./ui"

type Step = { step: string; sessions: number }
interface FunnelsData { paper: Step[]; signup: Step[]; store: Step[]; tools: Step[] }

const FUNNELS: { key: keyof FunnelsData; title: string; note: string; color: string }[] = [
  { key: "paper", title: "Studying past papers", note: "Visits that reach a past-paper page and then open or download a paper.", color: COLORS.blue },
  { key: "signup", title: "Signing in", note: "Signed-out visits that open the login page and finish signing in.", color: COLORS.green },
  { key: "store", title: "Buying from the store", note: "Each step must happen after the one before, in the same visit.", color: COLORS.amber },
  { key: "tools", title: "Using the question tools", note: "Visits to the Worksheet Generator or Test Builder that produce a PDF.", color: COLORS.purple },
]

function Funnel({ steps, color }: { steps: Step[]; color: string }) {
  const first = steps[0]?.sessions ?? 0
  if (first === 0) return <Empty />
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
      {steps.map((s, i) => {
        const prev = i === 0 ? s.sessions : steps[i - 1].sessions
        const ofFirst = first ? Math.round((s.sessions / first) * 1000) / 10 : 0
        const drop = i > 0 && prev ? Math.round((1 - s.sessions / prev) * 1000) / 10 : null
        // "Of which" rows are a subset of the step above, not a further step.
        const isSubset = s.step.startsWith("Of which")
        return (
          <div key={s.step} style={{ paddingLeft: isSubset ? "1rem" : 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", fontSize: "0.8rem", marginBottom: "0.3rem" }}>
              <span style={{ color: "var(--gm-text)" }}>{i + 1}. {s.step}</span>
              <span style={{ color: "var(--gm-text-2)", fontWeight: 600, flexShrink: 0 }}>
                {num(s.sessions)} <span style={{ color: "var(--gm-text-3)", fontWeight: 400 }}>· {ofFirst}%</span>
              </span>
            </div>
            <div style={{ height: "10px", background: "var(--gm-border)", borderRadius: "99px", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${ofFirst}%`, background: color, opacity: isSubset ? 0.6 : 1, borderRadius: "99px" }} />
            </div>
            {drop !== null && !isSubset && drop > 0 && (
              <p style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>{drop}% dropped off at this step</p>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function FunnelsPanel({ days }: { days: number }) {
  const { data, error, loading } = useSection<FunnelsData>("funnels", days, 300_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />
  return (
    <div style={panelGrid}>
      {FUNNELS.map(f => (
        <Panel key={f.key} title={f.title} note={f.note}>
          <Funnel steps={data[f.key]} color={f.color} />
        </Panel>
      ))}
    </div>
  )
}
