import Link from 'next/link'
import NewsletterForm from './NewsletterForm'

export default function Footer() {
  return (
    <footer
      aria-label="Site footer"
      style={{ background: "var(--gm-surface)", borderTop: "1px solid var(--gm-border)", color: "var(--gm-text-2)" }}
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
            <p style={{ fontWeight: 800, fontSize: "1.1rem", color: "var(--gm-text)", marginBottom: "0.75rem" }}>
              Grade<span style={{ color: "#F59E0B" }}>Max</span>
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                ["/about",                  "About Us"],
                ["/contact",                "Contact"],
                ["/edexcel-past-papers",    "Edexcel Past Papers"],
                ["/past-papers/cambridge",  "Cambridge Past Papers"],
                ["/edexcel-worksheets",     "Worksheet Generator"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
            </ul>
          </div>

          {/* IGCSE */}
          <div>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--gm-text)", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
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
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--gm-text)", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
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
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--gm-text)", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
              Features
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {([
                // Public landing (indexable) rather than the auth-walled /generate tool.
                ["/edexcel-worksheets",    "Worksheet Generator"],
                ["/test-builder",          "Test Builder"],
                ["/past-papers",           "Edexcel Papers by Year"],
                ["/past-papers/cambridge", "Cambridge Papers by Year"],
                ["/subjects",              "All Subjects"],
              ] as [string, string][]).map(([href, label]) => (
                <li key={href}><Link href={href} className="gm-link" style={{ fontSize: "0.8rem" }}>{label}</Link></li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--gm-text)", marginBottom: "0.875rem", letterSpacing: "0.04em" }}>
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

          {/* Newsletter */}
          <div>
            <NewsletterForm />
          </div>
        </div>

        {/* Bottom bar */}
        <div style={{ borderTop: "1px solid var(--gm-border)", paddingTop: "1.25rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
          <p style={{ fontSize: "0.78rem", color: "var(--gm-text-3)" }}>
            © {new Date().getFullYear()} GradeMax. All rights reserved.
          </p>
          {/* Social links */}
          <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            <a href="https://x.com/grademaxx" target="_blank" rel="noopener noreferrer" aria-label="GradeMax on X (Twitter)" style={{ color: "var(--gm-text-3)", transition: "color 0.15s" }} className="gm-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.259 5.633 5.905-5.633Zm-1.161 17.52h1.833L7.084 4.126H5.117Z"/>
              </svg>
            </a>
            <a href="https://www.reddit.com/r/grademax" target="_blank" rel="noopener noreferrer" aria-label="GradeMax on Reddit" style={{ color: "var(--gm-text-3)", transition: "color 0.15s" }} className="gm-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/>
              </svg>
            </a>
            <a href="https://www.instagram.com/grademax.me" target="_blank" rel="noopener noreferrer" aria-label="GradeMax on Instagram" style={{ color: "var(--gm-text-3)", transition: "color 0.15s" }} className="gm-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
              </svg>
            </a>
          </div>
        </div>

      </div>
    </footer>
  )
}
