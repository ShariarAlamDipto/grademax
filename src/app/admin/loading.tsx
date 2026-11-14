/**
 * Shown at once while the admin layout checks the session and role, so a slow
 * check reads as "loading" rather than as an empty page under the navbar.
 */
export default function AdminLoading() {
  return (
    <main style={{ maxWidth: "40rem", margin: "0 auto", padding: "4rem 1.25rem", color: "var(--gm-text-2)" }}>
      <p role="status" style={{ fontSize: "0.95rem" }}>Loading the admin portal…</p>
    </main>
  )
}
