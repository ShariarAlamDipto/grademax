"use client"
import { useEffect, useRef, type CSSProperties, type ReactNode } from "react"
import Link from "next/link"

/**
 * The three tool cards on the homepage: a line drawing that assembles itself
 * when the row scrolls into view, a title, one sentence, one dark button.
 * Styles live in src/app/design-refresh.css (.fc-*).
 */

const GOLD = "#F2B233"
const PAPER = "var(--gm-surface)"

/** Delay (seconds) for one stroke or fill, read by the .fc-s / .fc-f rules. */
function d(seconds: number): CSSProperties {
  return { ["--d" as string]: `${seconds}s` }
}

function Stroke({ path, delay = 0 }: { path: string; delay?: number }) {
  return <path className="fc-s" pathLength={1} d={path} style={d(delay)} />
}

const PastPapersArt = (
  <svg viewBox="0 0 240 130" aria-hidden>
    <g className="fc-lift">
      {/* mark scheme, behind */}
      <g transform="rotate(-9 92 66)">
        <rect className="fc-f" x="52" y="18" width="78" height="100" rx="7" fill={PAPER} />
        <rect className="fc-s" pathLength={1} x="52" y="18" width="78" height="100" rx="7" />
        <Stroke path="M64 40h40M64 54h54M64 68h46" delay={0.15} />
      </g>
      {/* question paper, in front */}
      <rect className="fc-f" x="104" y="12" width="84" height="106" rx="7" fill={PAPER} style={d(0.1)} />
      <rect className="fc-s" pathLength={1} x="104" y="12" width="84" height="106" rx="7" style={d(0.2)} />
      <Stroke path="M118 34h34M118 50h56M118 64h56M118 78h40M118 98h22" delay={0.4} />
      <circle className="fc-f" cx="182" cy="104" r="15" fill={GOLD} style={d(0.3)} />
      <path className="fc-s" pathLength={1} d="M175 104l5 5 9-10" style={{ ...d(1), stroke: "var(--gm-gold-ink)", strokeWidth: 2.2 }} />
    </g>
  </svg>
)

const WorksheetArt = (
  <svg viewBox="0 0 240 130" aria-hidden>
    <g className="fc-lift">
      {/* topic chips */}
      <rect className="fc-f" x="14" y="22" width="62" height="20" rx="10" fill={GOLD} />
      <rect className="fc-s" pathLength={1} x="14" y="22" width="62" height="20" rx="10" />
      <rect className="fc-s" pathLength={1} x="14" y="55" width="62" height="20" rx="10" style={d(0.1)} />
      <rect className="fc-f" x="14" y="88" width="62" height="20" rx="10" fill={GOLD} style={d(0.15)} />
      <rect className="fc-s" pathLength={1} x="14" y="88" width="62" height="20" rx="10" style={d(0.2)} />
      {/* chosen topics flow into the sheet */}
      <Stroke path="M78 32c26 0 28 22 54 22" delay={0.45} />
      <Stroke path="M78 98c26 0 28-22 54-22" delay={0.55} />
      {/* worksheet */}
      <rect className="fc-f" x="134" y="12" width="86" height="106" rx="7" fill={PAPER} style={d(0.1)} />
      <rect className="fc-s" pathLength={1} x="134" y="12" width="86" height="106" rx="7" style={d(0.7)} />
      <Stroke path="M148 32h30M148 50h58M148 62h58M148 80h58M148 92h44" delay={0.95} />
    </g>
  </svg>
)

const TestBuilderArt = (
  <svg viewBox="0 0 240 130" aria-hidden>
    <g className="fc-lift">
      <rect className="fc-f" x="30" y="10" width="180" height="110" rx="9" fill={PAPER} />
      <rect className="fc-s" pathLength={1} x="30" y="10" width="180" height="110" rx="9" />
      {/* three question rows; two are picked */}
      <rect className="fc-f" x="44" y="26" width="16" height="16" rx="4" fill={GOLD} style={d(0.3)} />
      <rect className="fc-s" pathLength={1} x="44" y="26" width="16" height="16" rx="4" style={d(0.2)} />
      <Stroke path="M70 34h86" delay={0.3} />
      <rect className="fc-s" pathLength={1} x="44" y="57" width="16" height="16" rx="4" style={d(0.4)} />
      <Stroke path="M70 65h64" delay={0.5} />
      <rect className="fc-f" x="44" y="88" width="16" height="16" rx="4" fill={GOLD} style={d(0.5)} />
      <rect className="fc-s" pathLength={1} x="44" y="88" width="16" height="16" rx="4" style={d(0.6)} />
      <Stroke path="M70 96h78" delay={0.7} />
      <path className="fc-s" pathLength={1} d="M48 34l3 3 6-6M48 96l3 3 6-6" style={{ ...d(1.1), stroke: "var(--gm-gold-ink)", strokeWidth: 2 }} />
      {/* marks total */}
      <Stroke path="M172 26h24v78h-24z" delay={0.8} />
      <Stroke path="M178 42h12M178 58h12M178 88h12" delay={1.1} />
    </g>
  </svg>
)

interface Feature {
  label: string
  heading: string
  body: string
  href: string
  cta: string
  art: ReactNode
}

const features: Feature[] = [
  {
    label: "Past Papers",
    heading: "Real exam papers, organised.",
    body: "Edexcel and Cambridge past papers, with Edexcel up to the 2026 series. Question papers and mark schemes by year, session and subject — all free.",
    href: "/past-papers",
    cta: "Browse papers",
    art: PastPapersArt,
  },
  {
    label: "Worksheets",
    heading: "Custom worksheets in seconds.",
    body: "Pick a subject, choose topics, set a year range — and get a targeted PDF worksheet with full mark scheme instantly.",
    // Public landing (indexable) rather than the auth-walled /generate tool.
    href: "/edexcel-worksheets",
    cta: "Build a worksheet",
    art: WorksheetArt,
  },
  {
    label: "Test Builder",
    heading: "Test your students' preparation.",
    body: "Teachers: hand-pick questions from real Edexcel papers, assemble a custom test, and download a print-ready PDF with mark scheme.",
    href: "/test-builder",
    cta: "Build a test",
    art: TestBuilderArt,
  },
]

export default function FeatureCards() {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = gridRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.setAttribute("data-visible", "1")
          obs.disconnect()
        }
      },
      { threshold: 0.15 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div ref={gridRef} className="fc-grid">
      {features.map((f, i) => (
        <Link key={f.label} href={f.href} className="fc-card" style={{ ["--delay" as string]: `${i * 0.12}s` }}>
          <div className="fc-art">{f.art}</div>
          <div className="fc-body">
            <p style={{ fontSize: "0.62rem", fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-text-3)", margin: 0 }}>
              {f.label}
            </p>
            <h3 className="fc-label">{f.heading}</h3>
            <p className="fc-text">{f.body}</p>
            <span className="btn-ink">{f.cta}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}
