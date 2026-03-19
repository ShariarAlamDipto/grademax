import { ImageResponse } from "next/og"

export const alt = "GradeMax - Free Edexcel IGCSE and A Level Past Papers"
export const size = { width: 1200, height: 630 }
export const contentType = "image/png"

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "linear-gradient(135deg, #000000 0%, #0a0a0a 50%, #111111 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background gradient circles */}
        <div
          style={{
            position: "absolute",
            top: -100,
            right: -100,
            width: 500,
            height: 500,
            borderRadius: 999,
              background: "radial-gradient(circle, rgba(104,126,52,0.15) 0%, transparent 70%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -80,
            left: -80,
            width: 400,
            height: 400,
            borderRadius: 999,
              background: "radial-gradient(circle, rgba(104,126,52,0.1) 0%, transparent 70%)",
          }}
        />

        {/* Content */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 48,
          }}
        >
          {/* Icon */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://grademax.me/favicon.png"
            width={140}
            height={140}
            alt="GradeMax logo"
            style={{ borderRadius: 28 }}
          />

          {/* Text */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span
              style={{
                fontSize: 72,
                fontWeight: 800,
                color: "#ffffff",
                fontFamily: "Georgia, serif",
                letterSpacing: -2,
              }}
            >
              GradeMax
            </span>
            <span
              style={{
                fontSize: 28,
                color: "rgba(255,255,255,0.6)",
                fontFamily: "sans-serif",
                marginTop: 8,
              }}
            >
              Free Edexcel IGCSE and A Level Past Papers
            </span>
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 4,
            background: "linear-gradient(90deg, #687E34 0%, #56692B 50%, #445322 100%)",
          }}
        />
      </div>
    ),
    { ...size }
  )
}
