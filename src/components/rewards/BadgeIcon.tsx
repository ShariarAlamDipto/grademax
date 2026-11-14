import type { BadgeGlyph, Tier } from "@/lib/rewards/badges"

/**
 * GradeMax's own badge artwork: a hexagonal medal whose metal shows the tier
 * and whose symbol shows the track. Drawn as SVG so it stays sharp at any size
 * and costs no image request.
 */

interface Metal {
  light: string
  dark: string
  rim: string
}

const METALS: Record<Tier | "locked", Metal> = {
  bronze:   { light: "#E3A066", dark: "#8F4E1E", rim: "#6E3A14" },
  silver:   { light: "#EEF1F5", dark: "#8C96A6", rim: "#6B7483" },
  gold:     { light: "#FDE68A", dark: "#D18A0A", rim: "#A16207" },
  platinum: { light: "#D8F3FF", dark: "#6E8FD8", rim: "#4C68B0" },
  locked:   { light: "#D9D4CA", dark: "#A9A396", rim: "#8F897C" },
}

/** 24×24 line symbols, one per badge track. */
const GLYPHS: Record<BadgeGlyph, string> = {
  stack:     "M4 8l8-4 8 4-8 4-8-4zM4 12.5l8 4 8-4M4 17l8 4 8-4",
  sheet:     "M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5",
  blueprint: "M4 5h16v14H4zM4 10h16M9 10v9",
  stopwatch: "M12 8a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM12 11v4l2.5 1.5M10 3h4M12 3v5",
  star:      "M12 3l2.7 5.6 6.1.8-4.5 4.3 1.1 6.1L12 16.9 6.6 19.8l1.1-6.1L3.2 9.4l6.1-.8z",
  pulse:     "M3 12h4l2.5-6 4 12 2.5-6h5",
  check:     "M12 3a9 9 0 100 18 9 9 0 000-18zM8 12l3 3 5-6",
  hands:     "M8 11a3 3 0 100-6 3 3 0 000 6zM16 11a3 3 0 100-6 3 3 0 000 6zM3 20c0-3 2.2-5 5-5s5 2 5 5M13 15.5c.9-.4 1.9-.5 3-.5 2.8 0 5 2 5 5",
  medal:     "M8 3l4 6 4-6M12 9a6 6 0 100 12 6 6 0 000-12zM12 12.5v5M10.5 13.5l1.5-1",
  flame:     "M12 3c1 3.5 5 5.5 5 10a5 5 0 01-10 0c0-2 1-3.2 2-4.2.3 1.6 1 2.4 2 2.7C10.5 8.5 11 5.5 12 3z",
  clipboard: "M9 4h6v3H9zM9 5.5H6v15h12v-15h-3M9 13l2 2 4-4",
}

const TIER_PIPS: Record<Tier, number> = { bronze: 1, silver: 2, gold: 3, platinum: 4 }

interface BadgeIconProps {
  /** Unique per badge on the page: SVG gradient ids are document-wide. */
  id: string
  glyph: BadgeGlyph
  tier: Tier | null
  size?: number
}

export function BadgeIcon({ id, glyph, tier, size = 64 }: BadgeIconProps) {
  const metal = METALS[tier ?? "locked"]
  const gradientId = `badge-metal-${id}`
  const pips = tier ? TIER_PIPS[tier] : 0

  return (
    <svg width={size} height={size * 1.125} viewBox="0 0 64 72" role="img" aria-label={tier ? `${tier} badge` : "Locked badge"}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={metal.light} />
          <stop offset="1" stopColor={metal.dark} />
        </linearGradient>
      </defs>
      {/* medal */}
      <path d="M32 2l26 15v30L32 62 6 47V17z" fill={`url(#${gradientId})`} stroke={metal.rim} strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M32 9l20 11.5v23L32 55 12 43.5v-23z" fill="#141B2E" opacity={tier ? 0.92 : 0.35} />
      {/* symbol */}
      <g transform="translate(20 20)" fill="none" stroke={tier ? metal.light : "#F4F1EA"} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d={GLYPHS[glyph]} />
      </g>
      {/* one pip per tier reached */}
      {Array.from({ length: pips }, (_, i) => (
        <circle key={i} cx={32 + (i - (pips - 1) / 2) * 8} cy={67.5} r={2.6} fill={metal.dark} stroke={metal.rim} strokeWidth="0.8" />
      ))}
    </svg>
  )
}
