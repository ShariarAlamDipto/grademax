"use client"
import { useEffect, useMemo, useState, type CSSProperties } from "react"
import OverviewPanel from "./analytics/OverviewPanel"
import CountriesPanel from "./analytics/CountriesPanel"
import RealtimePanel from "./analytics/RealtimePanel"
import BehaviorPanel from "./analytics/BehaviorPanel"
import AcquisitionPanel from "./analytics/AcquisitionPanel"
import FunnelsPanel from "./analytics/FunnelsPanel"
import RetentionPanel from "./analytics/RetentionPanel"
import PatternsPanel from "./analytics/PatternsPanel"
import ToolsPanel from "./analytics/ToolsPanel"
import PerformancePanel from "./analytics/PerformancePanel"
import { countryName, useSection } from "./analytics/ui"

/**
 * Admin → Analytics → Visitors. Anonymous first-party behaviour analytics
 * (migrations 36-40, beacons from <VisitTracker />). Each section loads its
 * own data from /api/admin/analytics/visitors?section=… with the range and
 * country chosen here.
 */
const SECTIONS = [
  { key: "overview", label: "Overview", ranged: true },
  { key: "countries", label: "Countries", ranged: true },
  { key: "realtime", label: "Realtime", ranged: false },
  { key: "behavior", label: "Behaviour", ranged: true },
  { key: "acquisition", label: "Acquisition", ranged: true },
  { key: "funnels", label: "Funnels", ranged: true },
  { key: "retention", label: "Retention", ranged: false },
  { key: "patterns", label: "Time & tech", ranged: true },
  { key: "tools", label: "Tools & health", ranged: true },
  { key: "performance", label: "Performance", ranged: true },
] as const

const RANGES = [
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "7", label: "7 days" },
  { key: "30", label: "30 days" },
  { key: "90", label: "90 days" },
  { key: "custom", label: "Custom" },
] as const

type SectionKey = (typeof SECTIONS)[number]["key"]
type RangeKey = (typeof RANGES)[number]["key"]

const pill = (active: boolean): CSSProperties => ({
  padding: "0.35rem 0.8rem", fontSize: "0.75rem", borderRadius: "99px", cursor: "pointer", whiteSpace: "nowrap",
  border: "1px solid var(--gm-border)", fontWeight: active ? 700 : 500,
  background: active ? "var(--gm-blue)" : "transparent", color: active ? "#fff" : "var(--gm-text-2)",
})
const field: CSSProperties = {
  padding: "0.35rem 0.5rem", fontSize: "0.75rem", borderRadius: "0.45rem",
  border: "1px solid var(--gm-border)", background: "var(--gm-bg)", color: "var(--gm-text)",
}

/**
 * VisitTracker stops counting a browser once it opens the admin panel
 * (localStorage "gm_staff"), so staff browsing does not inflate the numbers.
 * This lets an admin see that, and count their browser again (e.g. to check
 * Realtime after a deploy).
 */
function StaffBrowserNote() {
  const [excluded, setExcluded] = useState<boolean | null>(null)
  useEffect(() => {
    try { setExcluded(window.localStorage.getItem("gm_staff") === "1") } catch { setExcluded(null) }
  }, [])
  if (excluded === null) return null
  const toggle = () => {
    try {
      if (excluded) window.localStorage.removeItem("gm_staff")
      else window.localStorage.setItem("gm_staff", "1")
      setExcluded(!excluded)
    } catch { /* storage blocked */ }
  }
  return (
    <> This browser is {excluded ? "not counted (staff)" : "counted"} · <button
      onClick={toggle}
      style={{ background: "none", border: "none", color: "var(--gm-blue)", cursor: "pointer", padding: 0, font: "inherit" }}
    >{excluded ? "count it" : "stop counting it"}</button>{excluded ? " (it stops again the next time it opens the admin panel)." : "."}</>
  )
}

export default function VisitorAnalytics() {
  const [section, setSection] = useState<SectionKey>("overview")
  const [range, setRange] = useState<RangeKey>("30")
  const [from, setFrom] = useState("")
  const [to, setTo] = useState("")
  const [country, setCountry] = useState("")
  const ranged = SECTIONS.find(s => s.key === section)?.ranged

  // Countries seen in the last 90 days, for the filter.
  const { data: countryList } = useSection<{ countries: { country: string; visitors: number }[] }>("countries", "range=90", 600_000)
  const countryOptions = countryList?.countries ?? []

  const customReady = range === "custom" && from !== "" && to !== "" && from <= to
  const query = useMemo(() => {
    const params = new URLSearchParams()
    if (range === "custom") {
      if (customReady) { params.set("range", "custom"); params.set("from", from); params.set("to", to) }
      else params.set("range", "30")
    } else params.set("range", range)
    if (country) params.set("country", country)
    return params.toString()
  }, [range, from, to, country, customReady])

  const panelProps = { query, onPickCountry: (cc: string) => { setCountry(cc); setSection("overview") } }

  return (
    <div>
      <div role="tablist" aria-label="Visitor analytics sections" style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "0.9rem" }}>
        {SECTIONS.map(s => (
          <button key={s.key} role="tab" aria-selected={section === s.key} onClick={() => setSection(s.key)} style={pill(section === s.key)}>
            {s.label}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center", marginBottom: "0.75rem" }}>
        {ranged && (
          <div aria-label="Date range" style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
            {RANGES.map(r => (
              <button key={r.key} onClick={() => setRange(r.key)} style={{ ...pill(range === r.key), borderRadius: "0.5rem" }}>{r.label}</button>
            ))}
          </div>
        )}
        {ranged && range === "custom" && (
          <span style={{ display: "inline-flex", gap: "0.3rem", alignItems: "center", fontSize: "0.75rem", color: "var(--gm-text-3)" }}>
            <input type="date" aria-label="From" value={from} max={to || undefined} onChange={e => setFrom(e.target.value)} style={field} />
            to
            <input type="date" aria-label="To" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} style={field} />
            {!customReady && <span>pick both dates (showing 30 days)</span>}
          </span>
        )}
        {section !== "countries" && (
          <select aria-label="Country" value={country} onChange={e => setCountry(e.target.value)} style={{ ...field, marginLeft: "auto" }}>
            <option value="">All countries</option>
            {country && !countryOptions.some(c => c.country === country) && <option value={country}>{countryName(country)}</option>}
            {countryOptions.map(c => (
              <option key={c.country} value={c.country}>{countryName(c.country)} ({c.visitors.toLocaleString()})</option>
            ))}
          </select>
        )}
      </div>

      <p style={{ fontSize: "0.72rem", color: "var(--gm-text-3)", marginBottom: "1rem" }}>
        Anonymous: no names, emails or IP addresses. Days follow Bangladesh time. Ad blockers and the browser
        privacy signal (GPC) hide some visitors.<StaffBrowserNote />
        {country && section !== "countries" && (
          <> Showing <strong style={{ color: "var(--gm-text)" }}>{countryName(country)}</strong> only · <button
            onClick={() => setCountry("")}
            style={{ background: "none", border: "none", color: "var(--gm-blue)", cursor: "pointer", padding: 0, font: "inherit" }}
          >show all countries</button></>
        )}
      </p>

      {section === "overview" && <OverviewPanel {...panelProps} />}
      {section === "countries" && <CountriesPanel {...panelProps} />}
      {section === "realtime" && <RealtimePanel {...panelProps} />}
      {section === "behavior" && <BehaviorPanel {...panelProps} />}
      {section === "acquisition" && <AcquisitionPanel {...panelProps} />}
      {section === "funnels" && <FunnelsPanel {...panelProps} />}
      {section === "retention" && <RetentionPanel {...panelProps} />}
      {section === "patterns" && <PatternsPanel {...panelProps} />}
      {section === "tools" && <ToolsPanel {...panelProps} />}
      {section === "performance" && <PerformancePanel {...panelProps} />}
    </div>
  )
}
