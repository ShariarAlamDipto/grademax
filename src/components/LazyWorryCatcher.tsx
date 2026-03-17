"use client"
import dynamic from "next/dynamic"

const WorryCatcher = dynamic(() => import("@/components/WorryCatcher"), {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%",
      height: "360px",
      borderRadius: "1rem",
      border: "1px solid var(--gm-border-2)",
      background: "var(--gm-card-bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--gm-text-3)",
      fontSize: "0.82rem",
    }}>
      Loading…
    </div>
  ),
})

export default function LazyWorryCatcher() {
  return <WorryCatcher />
}
