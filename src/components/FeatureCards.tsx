"use client"
import { useEffect, useRef } from "react"
import Link from "next/link"

const features = [
  {
    icon: (
      <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    color: "#6EA8FE",
    bg: "rgba(110,168,254,0.08)",
    border: "rgba(110,168,254,0.20)",
    label: "Past Papers",
    heading: "Real exam papers, organised.",
    body: "Edexcel IGCSE past papers from 2011–2025. Question papers and mark schemes by year, session and subject — all free.",
    href: "/past-papers",
    cta: "Browse Papers →",
  },
  {
    icon: (
      <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h8m-8 4h4" />
        <rect x="14" y="12" width="7" height="7" rx="1" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    color: "#F59E0B",
    bg: "rgba(245,158,11,0.08)",
    border: "rgba(245,158,11,0.20)",
    label: "Worksheets",
    heading: "Custom worksheets in seconds.",
    body: "Pick a subject, choose topics, set a year range — and get a targeted PDF worksheet with full mark scheme instantly.",
    href: "/generate",
    cta: "Build Worksheet →",
  },
  {
    icon: (
      <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    color: "#A78BFA",
    bg: "rgba(167,139,250,0.08)",
    border: "rgba(167,139,250,0.20)",
    label: "Test Builder",
    heading: "Test your students' preparation.",
    body: "Teachers: hand-pick questions from real Edexcel papers, assemble a custom test, and download a print-ready PDF with mark scheme.",
    href: "/test-builder",
    cta: "Build a Test →",
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
      { threshold: 0.1 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div
      ref={gridRef}
      className="feature-card-grid"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gap: "1rem",
      }}
    >
      {features.map((f, i) => (
        <Link
          key={f.label}
          href={f.href}
          className="feature-card-item gm-card"
          style={{
            ["--delay" as string]: `${i * 0.1}s`,
            padding: "1.75rem 1.5rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
            textDecoration: "none",
            borderColor: f.border,
          }}
        >
          {/* Icon */}
          <div style={{
            width: "48px",
            height: "48px",
            borderRadius: "12px",
            background: f.bg,
            border: `1px solid ${f.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: f.color,
          }}>
            {f.icon}
          </div>

          {/* Label */}
          <span style={{
            fontSize: "0.6rem",
            fontWeight: 800,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: f.color,
          }}>
            {f.label}
          </span>

          {/* Heading */}
          <h3 style={{
            fontSize: "1rem",
            fontWeight: 700,
            color: "var(--gm-text)",
            lineHeight: 1.3,
            margin: 0,
          }}>
            {f.heading}
          </h3>

          {/* Body */}
          <p style={{
            fontSize: "0.82rem",
            color: "var(--gm-text-2)",
            lineHeight: 1.65,
            margin: 0,
            flex: 1,
          }}>
            {f.body}
          </p>

          {/* CTA */}
          <span style={{
            fontSize: "0.78rem",
            fontWeight: 600,
            color: f.color,
            marginTop: "0.25rem",
          }}>
            {f.cta}
          </span>
        </Link>
      ))}
    </div>
  )
}
