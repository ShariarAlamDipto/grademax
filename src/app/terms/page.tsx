import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'GradeMax Terms of Service - Read our terms and conditions for using the GradeMax study platform.',
}

const sectionStyle = { marginBottom: "2rem" }
const h2Style = { fontSize: "1.05rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.875rem" } as const
const pStyle = { color: "var(--gm-text-2)", lineHeight: 1.7, marginBottom: "0.875rem", fontSize: "0.9rem" } as const
const liStyle = { color: "var(--gm-text-2)", lineHeight: 1.7, fontSize: "0.9rem" }

export default function TermsPage() {
  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "3rem 1.5rem" }}>
        <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
          Terms of Service
        </h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem", marginBottom: "2.5rem" }}>Last updated: February 2026</p>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Agreement to Terms</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            By accessing or using GradeMax (grademax.me), you agree to be bound by these
            Terms of Service and all applicable laws and regulations. If you do not agree
            with any of these terms, you are prohibited from using or accessing this site.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Description of Service</h2>
          <p style={pStyle}>GradeMax provides an educational platform that allows students to:</p>
          <ul style={{ paddingLeft: "1.25rem", marginBottom: 0, display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>Generate custom worksheets from past examination papers</li>
            <li style={liStyle}>Browse and practice topic-wise questions</li>
            <li style={liStyle}>Access mark schemes for self-assessment</li>
            <li style={liStyle}>Build custom timed tests from real exam questions</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Use License</h2>
          <p style={pStyle}>
            Permission is granted to temporarily access the materials on GradeMax for
            personal, non-commercial educational use only. This is the grant of a licence,
            not a transfer of title. Under this licence you may not:
          </p>
          <ul style={{ paddingLeft: "1.25rem", marginBottom: 0, display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>Modify or copy the materials except for personal study purposes</li>
            <li style={liStyle}>Use the materials for any commercial purpose</li>
            <li style={liStyle}>Attempt to reverse engineer any software contained on GradeMax</li>
            <li style={liStyle}>Remove any copyright or other proprietary notations from the materials</li>
            <li style={liStyle}>Transfer the materials to another person or mirror them on any other server</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Educational Content</h2>
          <p style={pStyle}>
            The examination questions and mark schemes provided on GradeMax are sourced
            from publicly available past papers and are provided for educational and
            revision purposes only.
          </p>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            All examination content remains the intellectual property of the respective
            examination boards (Pearson Edexcel, etc.). GradeMax does not claim ownership
            of this examination content.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>User Conduct</h2>
          <p style={pStyle}>When using GradeMax, you agree not to:</p>
          <ul style={{ paddingLeft: "1.25rem", marginBottom: 0, display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>Use the service for any unlawful purpose</li>
            <li style={liStyle}>Attempt to gain unauthorised access to any part of the service</li>
            <li style={liStyle}>Interfere with or disrupt the service or servers</li>
            <li style={liStyle}>Use automated systems or software to extract data from the service</li>
            <li style={liStyle}>Redistribute or sell generated worksheets commercially</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Disclaimer</h2>
          <p style={pStyle}>
            The materials on GradeMax are provided on an &apos;as is&apos; basis. GradeMax makes
            no warranties, expressed or implied, and disclaims all other warranties including
            implied warranties of merchantability, fitness for a particular purpose, or
            non-infringement of intellectual property rights.
          </p>
          <p style={pStyle}>GradeMax does not guarantee that:</p>
          <ul style={{ paddingLeft: "1.25rem", marginBottom: 0, display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>The service will meet your specific requirements</li>
            <li style={liStyle}>The service will be uninterrupted, timely, secure, or error-free</li>
            <li style={liStyle}>Results obtained from using the service will be accurate or reliable</li>
            <li style={liStyle}>Using the materials will guarantee any particular examination results</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Limitations</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            In no event shall GradeMax or its suppliers be liable for any damages
            (including loss of data or profit, or business interruption) arising out of
            the use or inability to use the materials on GradeMax.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Accuracy of Materials</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            The materials on GradeMax could include technical, typographical, or
            photographic errors. GradeMax does not warrant that any materials are accurate,
            complete, or current, and may make changes at any time without notice.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Modifications</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            GradeMax may revise these terms at any time without notice. By using this
            website you agree to be bound by the then current version of these terms.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Governing Law</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            These terms are governed by and construed in accordance with applicable laws.
          </p>
        </section>

        <section>
          <h2 style={h2Style}>Contact</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            For questions about these Terms of Service, contact{' '}
            <a href="mailto:legal@grademax.me" style={{ color: "var(--gm-blue)", textDecoration: "none" }}>
              legal@grademax.me
            </a>.
          </p>
        </section>
      </div>
    </main>
  )
}
