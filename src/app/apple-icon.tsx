import { ImageResponse } from "next/og"

export const size = { width: 180, height: 180 }
export const contentType = "image/png"

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 180,
          height: 180,
          borderRadius: 36,
          background: "linear-gradient(135deg, #0a0a0a 0%, #111111 100%)",
          border: "2px solid rgba(104,126,52,0.35)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Centered G */}
        <span
          style={{
            fontSize: 110,
            fontWeight: 800,
            color: "#687E34",
            fontFamily: "Georgia, serif",
            lineHeight: 1,
            marginTop: -8,
          }}
        >
          G
        </span>
        {/* MAX below */}
        <span
          style={{
            fontSize: 32,
            fontWeight: 700,
            color: "#687E34",
            fontFamily: "Arial, sans-serif",
            letterSpacing: 6,
            marginTop: -4,
            opacity: 0.9,
          }}
        >
          MAX
        </span>
      </div>
    ),
    { ...size }
  )
}
