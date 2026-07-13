import type { Metadata } from "next"
import SuggestionForm from "./SuggestionForm"

export const metadata: Metadata = {
  title: "Improvements & Suggestions",
  description:
    "Share what you'd like to see on GradeMax. Every suggestion goes straight to the team and helps shape the platform.",
}

const CONTACT_EMAIL = "grademax.me@gmail.com"

export default function ImprovementsPage() {
  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "4rem 1.5rem 5rem" }}>

        {/* Eyebrow */}
        <p style={{
          textAlign: "center",
          fontSize: "0.7rem",
          fontWeight: 700,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: "var(--gm-amber)",
          marginBottom: "1rem",
        }}>
          Your voice shapes GradeMax
        </p>

        {/* Heading */}
        <h1 style={{
          textAlign: "center",
          fontSize: "clamp(1.6rem, 4.2vw, 2.4rem)",
          fontWeight: 800,
          lineHeight: 1.18,
          letterSpacing: "-0.02em",
          color: "var(--gm-text)",
          marginBottom: "0.75rem",
        }}>
          Drop your suggestions that you&apos;d like to see for{" "}
          <span style={{ color: "var(--gm-amber)" }}>GradeMax</span>
          {" "}— I&apos;ll try to implement them.
        </h1>

        <p style={{
          textAlign: "center",
          fontSize: "0.95rem",
          color: "var(--gm-text-2)",
          marginBottom: "2.5rem",
          lineHeight: 1.6,
        }}>
          New features, bug reports, subject requests, design ideas — anything goes.
        </p>

        {/* Form card (the standout element) */}
        <section style={{
          background: "var(--gm-card-bg)",
          border: "1px solid var(--gm-border-2)",
          borderRadius: "1.1rem",
          padding: "1.75rem",
          marginBottom: "1.25rem",
          boxShadow: "0 10px 40px rgba(0,0,0,0.18)",
        }}>
          <SuggestionForm />
        </section>

        {/* Contact divider */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          margin: "2rem 0 1.25rem",
        }}>
          <div style={{ flex: 1, height: 1, background: "var(--gm-border)" }} />
          <span style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--gm-text-3)" }}>
            Or email me directly
          </span>
          <div style={{ flex: 1, height: 1, background: "var(--gm-border)" }} />
        </div>

        {/* Email contact card */}
        <a
          href={`mailto:${CONTACT_EMAIL}?subject=GradeMax%20suggestion`}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            padding: "1.1rem 1.25rem",
            background: "var(--gm-card-bg)",
            border: "1px solid var(--gm-border-2)",
            borderRadius: "0.85rem",
            textDecoration: "none",
            color: "var(--gm-text)",
            transition: "border-color 0.15s ease, transform 0.1s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
            <div style={{
              width: "2.25rem",
              height: "2.25rem",
              borderRadius: "0.5rem",
              background: "rgba(245,158,11,0.15)",
              border: "1px solid rgba(245,158,11,0.35)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gm-amber)" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l9 6 9-6M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p style={{ margin: 0, fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gm-text-3)" }}>Contact us</p>
              <p style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600, color: "var(--gm-text)" }}>{CONTACT_EMAIL}</p>
            </div>
          </div>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gm-text-3)" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </a>

        {/* About GradeMax */}
        <section style={{
          marginTop: "4rem",
          paddingTop: "2.5rem",
          borderTop: "1px solid var(--gm-border)",
        }}>
          <p style={{
            fontSize: "0.7rem",
            fontWeight: 700,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--gm-text-3)",
            marginBottom: "0.75rem",
          }}>
            About GradeMax
          </p>
          <h2 style={{
            fontSize: "clamp(1.25rem, 3vw, 1.6rem)",
            fontWeight: 800,
            letterSpacing: "-0.01em",
            color: "var(--gm-text)",
            marginBottom: "1.25rem",
            lineHeight: 1.25,
          }}>
            A personal project, built for students and faculty alike.
          </h2>
          <div style={{
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
            fontSize: "0.95rem",
            color: "var(--gm-text-2)",
            lineHeight: 1.75,
          }}>
            <p>
              GradeMax is a personal project of mine, built to help my students prepare for their
              Edexcel IGCSE exams to the best of their ability. That&apos;s why worksheet generation
              sits at the heart of it — so students can target the chapter-wise areas they need to
              work on most.
            </p>
            <p>
              It was also built for myself and my fellow faculty, to make creating exam papers
              easier and save us all time.
            </p>
            <p>
              The website is still in its early development phase, but the response from all of you
              has been incredibly kind and supportive. To make GradeMax better I&apos;ll need your
              help — there are known issues with the markscheme links and past paper matches, and
              any community support is genuinely appreciated.
            </p>
            <p>
              Feel free to reach out at{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                style={{ color: "var(--gm-amber)", fontWeight: 600, textDecoration: "none" }}
              >
                {CONTACT_EMAIL}
              </a>
              .
            </p>
          </div>
        </section>

      </div>
    </main>
  )
}
