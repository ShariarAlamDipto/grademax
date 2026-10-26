"use client"
import {
  COLORS, DataTable, Panel, PeriodNote, RankList, SectionState, Stat, formatSeconds, num, panelGrid,
  statGrid, useSection, type PanelProps,
} from "./ui"

type Named = { name: string; count: number; visitors?: number }
interface ContentData {
  first_day: string; last_day: string; partial: boolean
  subjects: { subject: string; views: number; visitors: number; avg_engaged: number | null }[]
  years: { year: string; views: number }[]
  downloads: { total: number; visitors: number; by_level: Named[]; by_kind: Named[]; by_subject: Named[]; by_year: Named[]; by_series: Named[] }
  paper_opens: { total: number; by_subject: Named[]; by_doc: Named[]; by_view: Named[]; top_papers: { title: string; count: number }[] }
}

// URL slugs and file names into readable subject names.
const pretty = (slug: string) => slug.replace(/[-_]+/g, " ").replace(/\b\w/g, c => c.toUpperCase())
const SERIES: Record<string, string> = { "may-jun": "May/June", "oct-nov": "Oct/Nov", jan: "January", "feb-mar": "Feb/March", june: "June", nov: "November" }

export default function ContentPanel({ query }: PanelProps) {
  const { data, error, loading } = useSection<ContentData>("content", query, 300_000)
  if (!data) return <SectionState loading={loading} error={error} hasData={false} />

  const d = data.downloads, o = data.paper_opens
  const ms = o.by_doc.find(x => x.name === "Mark scheme")?.count ?? 0
  const split = o.by_view.find(x => x.name.startsWith("Side"))?.count ?? 0

  return (
    <div>
      <PeriodNote firstDay={data.first_day} lastDay={data.last_day} partial={data.partial}
        extra="paper opens are counted by the server for every country; pages and downloads follow the country filter" />
      <div style={statGrid}>
        <Stat title="Papers opened" value={num(o.total)} note="in the paper viewer (server count)" color={COLORS.blue} />
        <Stat title="Mark schemes" value={o.total ? `${Math.round((ms / o.total) * 100)}%` : "—"} note="of papers opened" color={COLORS.purple} />
        <Stat title="Side by side" value={o.total ? `${Math.round((split / o.total) * 100)}%` : "—"} note="opened question paper and mark scheme together" color={COLORS.cyan} />
        <Stat title="PDF downloads" value={num(d.total)} note={`by ${num(d.visitors)} visitors`} color={COLORS.green} />
      </div>

      <div style={panelGrid}>
        <Panel title="Most opened papers">
          <RankList rows={o.top_papers.map(p => ({ name: p.title, value: p.count }))} />
        </Panel>
        <Panel title="Papers opened by subject">
          <RankList rows={o.by_subject.map(s => ({ name: s.name, value: s.count, color: COLORS.purple }))} />
        </Panel>
      </div>

      <Panel title="Subject pages" note="Visits to /past-papers/<subject> pages, with the average reading time per page." style={{ marginBottom: "1.5rem" }}>
        <DataTable
          rows={data.subjects}
          initialSort="views"
          exportName="subjects"
          searchText={r => pretty(r.subject)}
          columns={[
            { key: "subject", title: "Subject", render: r => pretty(r.subject), sort: r => r.subject, csv: r => pretty(r.subject) },
            { key: "views", title: "Page views", align: "right", render: r => num(r.views), sort: r => r.views },
            { key: "visitors", title: "Visitors", align: "right", render: r => num(r.visitors), sort: r => r.visitors },
            { key: "time", title: "Reading time", align: "right", render: r => formatSeconds(r.avg_engaged), sort: r => r.avg_engaged ?? -1 },
          ]}
        />
      </Panel>

      <div style={panelGrid}>
        <Panel title="Downloads by subject">
          <RankList rows={d.by_subject.map(s => ({ name: pretty(s.name), value: s.count, sub: s.visitors ? `· ${num(s.visitors)} visitors` : undefined, color: COLORS.green }))} />
        </Panel>
        <Panel title="Downloads by qualification">
          <RankList rows={d.by_level.map(s => ({ name: s.name.toUpperCase().replace("CAMBRIDGE ", "Cambridge "), value: s.count, color: COLORS.cyan }))} />
        </Panel>
        <Panel title="What was downloaded">
          <RankList rows={d.by_kind.map(s => ({ name: s.name, value: s.count, color: COLORS.amber }))} />
        </Panel>
        <Panel title="Exam series downloaded">
          <RankList rows={d.by_series.map(s => ({ name: SERIES[s.name] ?? s.name, value: s.count, color: COLORS.pink }))} />
        </Panel>
        <Panel title="Exam years in demand" note="Downloads by the year of the paper.">
          <RankList rows={d.by_year.map(y => ({ name: y.name, value: y.count, color: COLORS.blue }))} />
        </Panel>
        <Panel title="Years browsed" note="Visits to past-paper pages for a specific year.">
          <RankList rows={data.years.map(y => ({ name: y.year, value: y.views, color: COLORS.slate }))} />
        </Panel>
      </div>
    </div>
  )
}
