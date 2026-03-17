import Link from 'next/link'

export default function Footer() {
  return (
    <footer
      aria-label="Site footer"
      style={{ background: "#0B1020", borderTop: "1px solid #1F2937", color: "#9CA3AF" }}
    >
      <div style={{ maxWidth: "1080px", margin: "0 auto", padding: "3.5rem 1.5rem 2rem" }}>

        {/* Link grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: "2rem",
            marginBottom: "2.5rem",
          }}
        >
          {/* Brand */}
          <div>
            <p style={{ fontWeight: 800, fontSize: "1.1rem", color: "#E5E7EB", marginBottom: "0.75rem" }}>
              Grade<span style={{ color: "#F59E0B" }}>Max</span>
            </p>
            <p style={{ fontSize: "0.8rem", lineHeight: 1.65, color: "#6B7280", marginBottom: "1rem" }}>
              Free Edexcel IGCSE &amp; A Level past papers with mark schemes.
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                ["/about",              "About Us"],
                ["/contact",            "Contact"],
                ["/edexcel-past-papers","Edexcel Past Papers"],
                ["/edexcel-worksheets", "Worksheet Generator"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
            </ul>
          </div>

          {/* IGCSE */}
          <div>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "#E5E7EB", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
              IGCSE Past Papers
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                ["/subjects/igcse/physics",   "Physics (4PH1)"],
                ["/subjects/igcse/maths-a",   "Maths A (4MA1)"],
                ["/subjects/igcse/maths-b",   "Maths B (4MB1)"],
                ["/subjects/igcse/chemistry", "Chemistry (4CH1)"],
                ["/subjects/igcse/biology",   "Biology (4BI1)"],
                ["/subjects/igcse/ict",       "ICT (4IT1)"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
              <li style={{ marginTop: "0.25rem" }}>
                <Link href="/edexcel-igcse-past-papers" style={{ color: "#6EA8FE", fontSize: "0.75rem", textDecoration: "none" }}>
                  View all IGCSE →
                </Link>
              </li>
            </ul>
          </div>

          {/* A Level */}
          <div>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "#E5E7EB", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
              A Level Past Papers
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                ["/subjects/ial/pure-mathematics-1","Pure Maths 1 (WMA11)"],
                ["/subjects/ial/mechanics-1",       "Mechanics 1 (WME01)"],
                ["/subjects/ial/statistics-1",      "Statistics 1 (WST01)"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
              <li style={{ marginTop: "0.25rem" }}>
                <Link href="/edexcel-a-level-past-papers" style={{ color: "#A78BFA", fontSize: "0.75rem", textDecoration: "none" }}>
                  View all A Level →
                </Link>
              </li>
            </ul>
          </div>

          {/* Features */}
          <div>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "#E5E7EB", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
              Features
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                ["/generate",    "Worksheet Generator"],
                ["/test-builder","Test Builder"],
                ["/browse",      "Browse by Topic"],
                ["/past-papers", "Past Papers by Year"],
                ["/subjects",    "All Subjects"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "#E5E7EB", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
              Legal
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                ["/privacy","Privacy Policy"],
                ["/terms",  "Terms of Service"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
            </ul>
          </div>
        </div>

        {/* SEO description */}
        <div style={{ borderTop: "1px solid #1F2937", paddingTop: "1.75rem", marginBottom: "1.25rem" }}>
          <p style={{ fontSize: "0.75rem", color: "#6B7280", lineHeight: 1.7, maxWidth: "780px", margin: "0 auto", textAlign: "center" }}>
            GradeMax is a free platform for Edexcel IGCSE and A Level past papers, question papers, and
            mark schemes. Practice topic-wise questions for Physics, Mathematics, Chemistry, Biology, and ICT.
            Generate custom worksheets from real Pearson Edexcel exam papers. All resources are free — no sign-up required.
          </p>
        </div>

        {/* Bottom bar */}
        <div style={{ borderTop: "1px solid #1F2937", paddingTop: "1.25rem", textAlign: "center" }}>
          <p style={{ fontSize: "0.78rem", color: "#6B7280" }}>
            © {new Date().getFullYear()} GradeMax. All rights reserved.
          </p>
          <p style={{ fontSize: "0.72rem", color: "#4B5563", marginTop: "0.4rem" }}>
            Free Edexcel past papers and custom worksheets for IGCSE &amp; A Level students worldwide · Papers available 2010–2025
          </p>
        </div>

      </div>
    </footer>
  )
}
