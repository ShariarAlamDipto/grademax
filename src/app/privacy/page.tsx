import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'GradeMax Privacy Policy - Learn how we collect, use, and protect your personal information.',
}

const sectionStyle = { marginBottom: "2rem" }
const h2Style = { fontSize: "1.05rem", fontWeight: 700, color: "var(--gm-text)", marginBottom: "0.875rem" } as const
const h3Style = { fontSize: "0.95rem", fontWeight: 600, color: "var(--gm-text)", marginBottom: "0.5rem" } as const
const pStyle = { color: "var(--gm-text-2)", lineHeight: 1.7, marginBottom: "0.875rem", fontSize: "0.9rem" } as const
const liStyle = { color: "var(--gm-text-2)", lineHeight: 1.7, fontSize: "0.9rem" }

export default function PrivacyPage() {
  return (
    <main style={{ background: "var(--gm-bg)", color: "var(--gm-text)", minHeight: "100vh" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "3rem 1.5rem" }}>
        <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.5rem)", fontWeight: 800, color: "var(--gm-text)", letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: "0.75rem" }}>
          Privacy Policy
        </h1>
        <p style={{ color: "var(--gm-text-3)", fontSize: "0.875rem", marginBottom: "2.5rem" }}>Last updated: February 2026</p>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Introduction</h2>
          <p style={pStyle}>
            GradeMax is committed to protecting your privacy.
            This Privacy Policy explains how GradeMax collects, uses, discloses, and safeguards your
            information when you visit grademax.me.
          </p>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            Please read this policy carefully. If you do not agree with these terms,
            please do not access the site.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Information Collected</h2>
          <h3 style={h3Style}>Information You Provide</h3>
          <p style={pStyle}>Information voluntarily provided when using GradeMax services, including:</p>
          <ul style={{ paddingLeft: "1.25rem", marginBottom: "1rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>Email address (when contacting or creating an account)</li>
            <li style={liStyle}>Feedback and correspondence</li>
            <li style={liStyle}>Any other information you choose to provide</li>
          </ul>
          <h3 style={h3Style}>Automatically Collected Information</h3>
          <p style={pStyle}>When you access the website, the following may be collected automatically:</p>
          <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>Browser type and version</li>
            <li style={liStyle}>Operating system</li>
            <li style={liStyle}>Pages visited and time spent</li>
            <li style={liStyle}>Referring website</li>
            <li style={liStyle}>Device information</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>How Information Is Used</h2>
          <p style={pStyle}>The information collected is used to:</p>
          <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <li style={liStyle}>Provide, operate, and maintain the website</li>
            <li style={liStyle}>Improve, personalise, and expand services</li>
            <li style={liStyle}>Understand and analyse how you use the website</li>
            <li style={liStyle}>Develop new features</li>
            <li style={liStyle}>Communicate for customer service and support</li>
            <li style={liStyle}>Detect and prevent fraud</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Analytics</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            Vercel Analytics is used to collect anonymous usage data to help understand how visitors
            use the website. This data is aggregated and does not personally identify you.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Cookies</h2>
          <p style={pStyle}>
            Cookies and similar tracking technologies may be used to track activity and hold certain
            information. You can instruct your browser to refuse all cookies; however, some portions
            of the service may not function without them.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Data Security</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            Appropriate technical and organisational security measures are in place to protect your
            personal information. No method of transmission over the internet is 100% secure.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Third-Party Services</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            Third-party companies may be employed to facilitate the service or assist in analysis.
            These parties access your information only to perform specific tasks and are obligated
            not to disclose or use it for any other purpose.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Children&apos;s Privacy</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            GradeMax is designed for students of all ages. Personally identifiable information is not
            knowingly collected from children under 13 without parental consent. If you are a parent
            or guardian and believe your child has provided personal information, please contact us.
          </p>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Changes to This Policy</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            This Privacy Policy may be updated from time to time. Changes will be posted on this page
            with an updated date.
          </p>
        </section>

        <section>
          <h2 style={h2Style}>Contact</h2>
          <p style={{ ...pStyle, marginBottom: 0 }}>
            For questions about this Privacy Policy, contact{' '}
            <a href="mailto:privacy@grademax.me" style={{ color: "var(--gm-blue)", textDecoration: "none" }}>
              privacy@grademax.me
            </a>.
          </p>
        </section>
      </div>
    </main>
  )
}
