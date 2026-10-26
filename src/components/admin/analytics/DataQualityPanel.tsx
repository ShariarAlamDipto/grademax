"use client"
import {
  COLORS, DataTable, Empty, Panel, PeriodNote, SectionState, Stat, countryName, formatSeconds, num, pct,
  panelGrid, statGrid, useSection, type PanelProps,
} from "./ui"

interface Recon { name: string; source: string; truth: number; tracked: number; tracked_label: string; ratio: number | null }
interface QualityData {
  first_day: string; last_day: string; partial: boolean
  reconciliation: Recon[]
  coverage: { page_views: number; country_known: number | null; engagement_known: number | null; scroll_known: number | null; landing_with_lcp: number | null; events_with_visit: number | null }
  no_interaction_by_country: { country: string; sessions: number; no_interaction: number; share: number }[]
  heavy_sessions: { started: string; pages: number; downloads: number; minutes: number | null; engaged: number; country: string; device: string | null; browser: string | null; channel: string | null }[]
  freshness: { last_page_view: string | null; last_event: string | null; views_last_hour: number; views_last_day: number; tracking_since: string | null }
}

// What each comparison means and what a healthy ratio looks like.
const RECON_NOTES: Record<string, string> = {
  "Paper opens": "Server count includes crawlers that run no JavaScript; the tracker misses ad-blocked and privacy-protected browsers. A big gap means crawler traffic on the viewer.",
  "Worksheets": "Should be close to 100%. Below about 80% means many students block tracking.",
  "Saved tests": "Should be close to 100% (counted when the PDFs are ready).",
  "New accounts": "Below 100% is normal: accounts confirmed from another browser or device carry no visitor cookie.",
  "Orders": "Should be 100%; orders placed from a browser that blocks the cookie are missed.",
}

const ago = (iso: string | null) => {
  if (!iso) return "never"
  const m = Math.round((Date.now() - Date.parse(iso)) / 60000)
  return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`
}
const ratioColor = (r: number | null, name: string) =>
  r == null ? "var(--gm-text-3)" : name === "Paper opens" ? "var(--gm-text-2)" : r >= 80 && r <= 110 ? COLORS.green : COLORS.amber

export default function DataQualityPanel({ query }: PanelProps) {
  const { data, error, loading } = useSection<QualityData>("quality", query, 120_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const f = data.freshness, c = data.coverage
  const stale = !f.last_page_view || Date.now() - Date.parse(f.last_page_view) > 60 * 60 * 1000

  return (
    <div>
      <PeriodNote firstDay={data.first_day} lastDay={data.last_day} partial={data.partial} extra="how far to trust the other sections" />
      <div style={statGrid}>
        <Stat title="Tracking" value={stale ? "Silent" : "Live"} note={`last page view ${ago(f.last_page_view)}`} color={stale ? COLORS.pink : COLORS.green} />
        <Stat title="Page views, last hour" value={num(f.views_last_hour)} note={`${num(f.views_last_day)} in 24 hours`} color={COLORS.blue} />
        <Stat title="Country known" value={pct(c.country_known)} note="of page views (Cloudflare header)" color={(c.country_known ?? 0) >= 95 ? COLORS.green : COLORS.amber} />
        <Stat title="Reading time measured" value={pct(c.engagement_known)} note="of page views (lost when a phone kills the tab)" color={COLORS.cyan} />
        <Stat title="Page speed reported" value={pct(c.landing_with_lcp)} note="of landing pages (LCP)" color={COLORS.purple} />
      </div>

      <Panel title="Analytics vs the real records" note="Each line compares what the dashboard counted with the table that records the real thing." style={{ marginBottom: "1.5rem" }}>
        <DataTable<Recon>
          rows={data.reconciliation}
          exportName="reconciliation"
          columns={[
            { key: "name", title: "What", render: r => r.name, csv: r => r.name },
            { key: "truth", title: "Real records", align: "right", render: r => num(r.truth), csv: r => r.truth },
            { key: "tracked", title: "Analytics", align: "right", render: r => num(r.tracked), csv: r => r.tracked },
            { key: "ratio", title: "Seen", align: "right", csv: r => r.ratio, render: r => <span style={{ color: ratioColor(r.ratio, r.name), fontWeight: 700 }}>{pct(r.ratio)}</span> },
            { key: "meaning", title: "What it means", render: r => <span style={{ whiteSpace: "normal", color: "var(--gm-text-3)" }}>{RECON_NOTES[r.name] ?? r.source}</span>, csv: r => RECON_NOTES[r.name] ?? r.source },
          ]}
        />
      </Panel>

      <div style={panelGrid}>
        <Panel title="Visits with no interaction, by country" note="One page, no reading time, no clicks. A high share usually means automated traffic (or tabs opened and never looked at).">
          <DataTable rows={data.no_interaction_by_country} columns={[
            { key: "country", title: "Country", render: r => countryName(r.country) },
            { key: "sessions", title: "Visits", align: "right", render: r => num(r.sessions) },
            { key: "share", title: "No interaction", align: "right", render: r => <span style={{ color: r.share >= 40 && r.sessions >= 10 ? COLORS.pink : undefined, fontWeight: 600 }}>{r.share}%</span> },
          ]} />
        </Panel>
        <Panel title="Unusually heavy visits" note="60+ pages or 30+ downloads in one visit: a teacher collecting papers, or a scraper.">
          {data.heavy_sessions.length === 0 ? <Empty>None in this period.</Empty> : (
            <DataTable rows={data.heavy_sessions} columns={[
              { key: "when", title: "Started", render: r => new Date(r.started).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) },
              { key: "pages", title: "Pages", align: "right", render: r => num(r.pages) },
              { key: "dl", title: "Downloads", align: "right", render: r => num(r.downloads) },
              { key: "mins", title: "Minutes", align: "right", render: r => num(r.minutes) },
              { key: "read", title: "Reading", align: "right", render: r => formatSeconds(r.engaged) },
              { key: "who", title: "From", render: r => <span title={countryName(r.country)}>{`${r.country} · ${r.device ?? "?"} · ${r.browser ?? "?"}`}</span> },
            ]} />
          )}
        </Panel>
      </div>
    </div>
  )
}
