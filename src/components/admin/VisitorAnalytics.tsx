"use client"
import { useState } from "react"
import OverviewPanel from "./analytics/OverviewPanel"
import RealtimePanel from "./analytics/RealtimePanel"
import BehaviorPanel from "./analytics/BehaviorPanel"
import AcquisitionPanel from "./analytics/AcquisitionPanel"
import FunnelsPanel from "./analytics/FunnelsPanel"
import RetentionPanel from "./analytics/RetentionPanel"
import PatternsPanel from "./analytics/PatternsPanel"

/**
 * Admin → Analytics → Visitors. Anonymous first-party behaviour analytics
 * (migrations 36 and 37, beacons from <VisitTracker />). Each section loads
 * its own data from /api/admin/analytics/visitors?section=…
 */
const SECTIONS = [
  { key: "overview", label: "Overview", ranged: true },
  { key: "realtime", label: "Realtime", ranged: false },
  { key: "behavior", label: "Behaviour", ranged: true },
  { key: "acquisition", label: "Acquisition", ranged: true },
  { key: "funnels", label: "Funnels", ranged: true },
  { key: "retention", label: "Retention", ranged: false },
  { key: "patterns", label: "Time & tech", ranged: true },
] as const

type SectionKey = (typeof SECTIONS)[number]["key"]
const RANGES = [7, 30, 90] as const

const pill = (active: boolean) => ({
  padding: "0.35rem 0.8rem", fontSize: "0.75rem", borderRadius: "99px", cursor: "pointer", whiteSpace: "nowrap" as const,
  border: "1px solid var(--gm-border)", fontWeight: active ? 700 : 500,
  background: active ? "var(--gm-blue)" : "transparent", color: active ? "#fff" : "var(--gm-text-2)",
})

export default function VisitorAnalytics() {
  const [section, setSection] = useState<SectionKey>("overview")
  const [days, setDays] = useState<(typeof RANGES)[number]>(30)
  const ranged = SECTIONS.find(s => s.key === section)?.ranged

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1.25rem" }}>
        <div role="tablist" aria-label="Visitor analytics sections" style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
          {SECTIONS.map(s => (
            <button key={s.key} role="tab" aria-selected={section === s.key} onClick={() => setSection(s.key)} style={pill(section === s.key)}>
              {s.label}
            </button>
          ))}
        </div>
        {ranged && (
          <div style={{ display: "flex", gap: "0.25rem" }} aria-label="Date range">
            {RANGES.map(r => (
              <button key={r} onClick={() => setDays(r)} style={{ ...pill(days === r), borderRadius: "0.5rem" }}>{r} days</button>
            ))}
          </div>
        )}
      </div>

      <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginBottom: "1rem" }}>
        Anonymous: no names, emails or IP addresses. Days follow Bangladesh time. Ad blockers hide some visitors.
      </p>

      {section === "overview" && <OverviewPanel days={days} />}
      {section === "realtime" && <RealtimePanel />}
      {section === "behavior" && <BehaviorPanel days={days} />}
      {section === "acquisition" && <AcquisitionPanel days={days} />}
      {section === "funnels" && <FunnelsPanel days={days} />}
      {section === "retention" && <RetentionPanel />}
      {section === "patterns" && <PatternsPanel days={days} />}
    </div>
  )
}
