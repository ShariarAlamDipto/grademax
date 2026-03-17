import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contact Us',
  description: 'Get in touch with the GradeMax team. We welcome your questions, feedback, and suggestions about our IGCSE and A Level study platform.',
}

export default function ContactPage() {
  return (
    <main style={{ background: "#060912", color: "#EDF0F7", minHeight: "100vh" }}>
      <div style={{ maxWidth: "640px", margin: "0 auto", padding: "3.5rem 1.5rem" }}>

        <div style={{ marginBottom: "3rem" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#F59E0B", marginBottom: "0.75rem" }}>
            GradeMax
          </p>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "#EDF0F7", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
            Get in touch
          </h1>
          <p style={{ color: "#9CA3AF", fontSize: "0.9rem", lineHeight: 1.6 }}>
            Questions, feedback, or subject requests — reach out directly.
          </p>
        </div>

        {/* Contact items */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0", marginBottom: "3rem" }}>
          {([
            { label: "General &amp; Support",  email: "shariardipto111@gmail.com", note: "Fastest response" },
            { label: "Feature Requests",       email: "shariardipto111@gmail.com", note: "Ideas welcome" },
            { label: "Bug Reports",            email: "shariardipto111@gmail.com", note: "Include details" },
          ] as { label: string; email: string; note: string }[]).map(({ label, email, note }, i, arr) => (
            <div
              key={label}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1.25rem 0",
                borderBottom: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none",
                gap: "1rem",
                flexWrap: "wrap",
              }}
            >
              <div>
                <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#EDF0F7", marginBottom: "0.2rem" }}
                   dangerouslySetInnerHTML={{ __html: label }} />
                <p style={{ fontSize: "0.75rem", color: "#6B7280" }}>{note}</p>
              </div>
              <a
                href={`mailto:${email}`}
                style={{ fontSize: "0.85rem", color: "#6EA8FE", textDecoration: "none", fontWeight: 500, transition: "color 0.15s" }}
              >
                {email}
              </a>
            </div>
          ))}
        </div>

        {/* Response time */}
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "1rem", padding: "1.5rem" }}>
          <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#EDF0F7", marginBottom: "0.4rem" }}>Response time</p>
          <p style={{ fontSize: "0.825rem", color: "#9CA3AF", lineHeight: 1.6 }}>
            Typically within 24–48 hours on weekdays. Subject requests are reviewed weekly.
          </p>
        </div>

      </div>
    </main>
  )
}
