"use client"
import { useEffect, useRef } from "react"
import Link from "next/link"

interface SubjectEntry {
  name: string
  level: string
  slug: string
  code: string
  color: string
  bg: string
  border: string
}

interface Props {
  subjects: SubjectEntry[]
  title: string
}

export default function SubjectGrid({ subjects, title }: Props) {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = gridRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { el.setAttribute("data-visible", "1"); obs.disconnect() } },
      { threshold: 0.1 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div>
      <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6B7280", marginBottom: "1rem" }}>
        {title}
      </p>
      <div ref={gridRef} className="subject-float-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
        {subjects.map((s, i) => (
          <Link
            key={s.slug}
            href={`/subjects/${s.level}/${s.slug}`}
            className="subject-float-item"
            style={{
              ["--delay" as string]: `${i * 0.07}s`,
              background: s.bg,
              border: `1px solid ${s.border}`,
              borderRadius: "1rem",
              padding: "1.25rem 1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.35rem",
              textDecoration: "none",
            }}
          >
            <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "#E5E7EB", lineHeight: 1.2 }}>{s.name}</p>
            <p style={{ fontSize: "0.6rem", fontWeight: 700, color: s.color, letterSpacing: "0.08em", textTransform: "uppercase" }}>{s.code}</p>
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.625rem" }}>
              <Link href={`/past-papers/${s.slug}`} onClick={e => e.stopPropagation()} style={{ fontSize: "0.7rem", color: s.color, opacity: 0.85, textDecoration: "none" }}>Papers →</Link>
              <Link href={`/subjects/${s.level}/${s.slug}`} onClick={e => e.stopPropagation()} style={{ fontSize: "0.7rem", color: "#6B7280", textDecoration: "none" }}>Topics →</Link>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
