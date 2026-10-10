import Link from "next/link"

const MESSAGE =
  "Need topic-wise explanation videos for any IAL or IGCSE Maths or Physics topic? Request one in the Improvements tab →"

/**
 * Scrolling announcement strip that sits directly under the fixed navbar.
 * The text is rendered twice so the loop in .gm-promo-track is seamless;
 * the second copy is hidden from screen readers.
 */
export default function PromoBanner() {
  return (
    <Link href="/improvements" className="gm-promo" aria-label={MESSAGE}>
      <span className="gm-promo-track" aria-hidden="true">
        <span className="gm-promo-item">{MESSAGE}</span>
        <span className="gm-promo-item">{MESSAGE}</span>
      </span>
    </Link>
  )
}
